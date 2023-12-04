import os
import shutil
import tarfile
from typing import List, Dict, Tuple

from config import bcolors, Deadline
from datetime import datetime, timedelta


def get_user_selection(available_options: List[str]) -> str:
    """
    Given a list of lab names, print them to the console in a user-friendly format and waits for the user to make a
    selection. The selection is validated against non-integer and out of range inputs.

    :param available_options: A list of labs
    :return: Name on the user selected lab
    """

    print(f"{bcolors.OKCYAN}Available Labs:{bcolors.ENDC}")
    for i, lab in enumerate(available_options):
        print(f"{bcolors.OKBLUE}[{i}]{bcolors.ENDC}", lab)

    while True:
        selected_option = input(
            f"{bcolors.OKGREEN}\nSelect your lab w/o brackets: {bcolors.ENDC}")

        try:
            selected_option = int(selected_option)
        except ValueError:
            print(f"{bcolors.FAIL}Please enter a valid number{bcolors.ENDC}")
            continue

        if selected_option >= len(available_options) or selected_option < 0:
            print(f"{bcolors.FAIL}Lab not found{bcolors.ENDC}")
        else:
            break

    return available_options[selected_option]


def extract_all(tar_file_path: str, extract_path: str) -> None:
    """
    Recursively extracts all .tar files inside submission.tar and save the output of all extractions in extract_path.

    :param tar_file_path: Path to the tar file that should be extracted
    :param extract_path: Save location of the untar content
    """

    start_files = os.listdir(extract_path)
    try:
        file = tarfile.open(tar_file_path)
        file.extractall(extract_path)

        new_files = os.listdir(extract_path)
        for file in new_files:
            if file in start_files:
                continue
            elif os.path.splitext(file)[1] == ".tar":
                extract_all(os.path.join(extract_path, file), extract_path)

    except tarfile.ReadError:
        print(tar_file_path, "failed")
    except EOFError:
        print(tar_file_path, "Cannot untar the file")


def parse_time_from_log(log_path: str) -> datetime:
    """
    Opens the log file and extracts the last line to read the final submission time of the student.

    :param log_path: Path to the log file
    :return: A datetime object of the final submission time
    """
    with open(log_path) as log_file:
        final_sub_details = log_file.readlines()[-1].strip()
        final_sub_time = final_sub_details.split("\t")[1].split(" ")

        # Take care of single digit dates. In the log file there is an additional '\t' character
        # between the month and the day if the day is a single digit. eg: Oct \t 10 vs Oct \t\t 2. This
        # get rids of the additional '\t' and pads the day with a 0
        if final_sub_time[2] == "":
            final_sub_time.pop(2)
            final_sub_time[2] = "0" + final_sub_time[2]

        final_sub_time = " ".join(final_sub_time[1:])
        final_sub_time = datetime.strptime(final_sub_time, "%b %d %H:%M:%S %Y")

        return final_sub_time


def print_and_get_sub_selection(lab_names: List[str]) -> int:
    """
    Print all the labs in the list to the terminal with the corresponding index. Then waits for the user input to select
    a lab based on the index. Returns the selected lab index to the calling function. Performs basic input verification.

    :param lab_names: A list of lab names as strings
    :return: The index of the selected lab
    """

    lab_names.sort()

    for i, lab in enumerate(lab_names):
        # Ignore folders that are hidden
        if not lab.startswith("."):
            print(f"{bcolors.OKBLUE}[{i}]{bcolors.ENDC}", lab)

    while True:
        lab_num = input("\nEnter lab number w/o brackets: ")

        try:
            lab_num = int(lab_num)
        except ValueError:
            print(f"{bcolors.FAIL}Please enter a valid number{bcolors.ENDC}")
            continue

        if lab_num >= len(lab_names) or lab_num < 0:
            print(f"{bcolors.FAIL}Lab not found{bcolors.ENDC}")
        else:
            return lab_num


def get_deadline_info(deadline: Deadline, assign=False) -> Tuple[datetime, List[timedelta], List[int]]:
    """
    Extract the current deadline, thresholds, and penalty values from the config file. The thresholds and penalties
    lists can have different number of elements. In such a case the minimum number of elements of both is selected.
    eg:
        \n\tThreshold: [30, 1440, 2880, 4320, 5760]
        \n\tPenalties: [0, 5, 10]
    Then the code will consider as there are only 3 penalty brackets.

    :param deadline: The deadline of the current lab
    :param assign: If true, the extended deadline system for assignments will be used
    :return: A tuple containing the current deadline, thresholds, and penalty
    """

    current_deadline = datetime.strptime(deadline.cur, "%Y/%m/%d %H:%M:%S")
    thresholds = deadline.thresholds

    if assign:
        penalties = deadline.assign_penalties
    else:
        penalties = deadline.lab_penalties

    num_stages = len(penalties)

    # Convert the threshold values in to timedelta for comparison
    thresholds = [timedelta(minutes=x) for x in thresholds[:num_stages]]

    return current_deadline, thresholds, penalties


def calculate_late_penalty(delayed_time: timedelta, thresholds: List[timedelta], penalties: List[int]) -> int:
    """
    Calculates the late submission penalty that should be added to a student based on how delayed the submission is.
    The number of late submission brackets is decided by taking the minimum number of elements available in two lists,
    thresholds and penalties.

    :param delayed_time: How late the submission is from the deadline
    :param thresholds: A list containing threshold values for each late submission bracket
    :param penalties: A list of penalties for each bracket
    :return: The submission penalty as an integer
    """
    rejected = False
    delay_penalty = None

    for threshold, penalty in zip(thresholds, penalties):
        if delayed_time <= threshold:
            delay_penalty = penalty
            break
    else:
        rejected = True  # If the delayed_time is not less than any of the brackets, the submission is rejected

    if rejected:
        return -1
    else:
        return delay_penalty


def get_submission_times(available_classes: List[str], lab_path: str) -> Tuple[Dict[str, datetime], Dict[str, str]]:
    """
    Iterates through all submissions inside the lab directory and extract the final submission from each submission.
    These are stored in a dictionary with the zID as the key and the time as the key. If there is an error with opening
    or reading the logfile, this information will be written to the error dict in the above same format.

    :param available_classes: List of available classes for selected lab
    :param lab_path: Absolute file path to the lab folder containing the classes
    :return: Two dictionaries containing the submission times and errors
    """
    submission_times = {}
    errors = {}

    for curr_class in available_classes:
        if curr_class.startswith("."):
            continue

        class_path = os.path.join(lab_path, curr_class)
        student_dirs = os.listdir(class_path)
        student_dirs.sort()

        for student_dir in student_dirs:
            if student_dir.startswith("."):
                continue
            try:
                log_path = os.path.join(class_path, student_dir, "log")
                submission_times[student_dir] = parse_time_from_log(log_path)

            except IndexError:
                errors[student_dir] = "IndexError"

            except FileNotFoundError:
                errors[student_dir] = "FileNotFound"

    return submission_times, errors


def check_pre_download_conditions(destination_path: str, lab_name: str) -> bool:
    """
    Before downloading the labs, check whether there are pre-existing submissions of the same lab in the download
    location. The user can select whether to overwrite these files if they exist, or they will be moved to a hidden
    folder prefixed with .lastrun and the new labs will be downloaded.

    :param destination_path: Location where the downloaded labs should be saved locally
    :param lab_name: Name of the lab being downloaded
    :return: Returns False if the user aborts the process
    """

    lab_path = os.path.join(destination_path, lab_name)
    lab_dir_exists = os.path.isdir(lab_path)

    if lab_dir_exists:
        overwrite = input(f"There is a {bcolors.WARNING}{lab_name}{bcolors.ENDC} directory available. "
                          f"{bcolors.FAIL}Do you wish to overwrite its content? y/[n]{bcolors.ENDC}: ")

        if overwrite.lower() == "y":
            return True
        else:
            continue_download = input(f"Do you wish to continue the download process? This will move all existing "
                                      f"directories inside {bcolors.WARNING}{lab_name}{bcolors.ENDC} to a hidden "
                                      f"directory before downloading the files. {bcolors.FAIL}y/[n]{bcolors.ENDC}: ")

            if continue_download.lower() == "y":
                existing_dirs = os.listdir(lab_path)
                to_be_moved_dirs = []  # To store the existing submissions
                num_runs = 0

                for directory in existing_dirs:
                    if directory.startswith(".lastrun"):
                        num_runs += 1
                    else:
                        to_be_moved_dirs.append(directory)

                lastrun_path = os.path.join(lab_path, f".lastrun_{num_runs}")
                os.mkdir(lastrun_path)

                for directory in to_be_moved_dirs:
                    shutil.move(os.path.join(lab_path, directory), lastrun_path)

                return True
            else:
                print(f"{bcolors.FAIL}Downloading {lab_name} Aborted!{bcolors.ENDC}")
                return False
    else:
        os.mkdir(lab_path)
        return True
