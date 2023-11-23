import os
import re
import shutil
import tarfile
import subprocess

from tqdm import tqdm
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from config import bcolors, Deadline
from connection.ssh import Client


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


def lab_selection(local_all_labs_path: str) -> Tuple[List[str], str]:
    """
    Lists down all available labs in the given path and prompts the user to pick a specific lab number.
    If the input lab number is present, returns all class names under the given lab and their respective directory paths

    :param local_all_labs_path: Path of the local save location of all labs
    :return: The available class names (eg: 'fri09-oboe') in the lab and the path of the lab directory
    """

    avail_labs = os.listdir(local_all_labs_path)
    lab_num = print_and_get_sub_selection(avail_labs)

    lab_path = os.path.join(local_all_labs_path, avail_labs[lab_num])
    avail_classes = os.listdir(lab_path)

    return avail_classes, lab_path


def get_deadline_info(deadline: Deadline, assign=False) -> Tuple[datetime, List[timedelta], List[int]]:
    """
    Extract the current deadline, thresholds, and penalty values from the config file. The thresholds and penalties
    lists can have different number of elements. In such a case the minimum number of elements of both is selected.
    eg:
        Threshold: [30, 1440, 2880, 4320, 5760]
        Penalties: [0, 5, 10]
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


def parse_time_from_log(log_path):
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


def get_submission_times(available_classes: List[str], lab_path: str, print_outputs: bool = True):
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
                if print_outputs:
                    errors[student_dir] = "FileNotFound"

    return submission_times, errors


def check_late_submission(available_classes: List[str], lab_path: str, deadline: Deadline,
                          assign=False) -> Dict[str, datetime]:
    """
    Takes the available classes and the lab path as the input and checks the time of the last submission for each
    student. Opens the log file of each submission and reads the final line to get the last submitted time. Then
    compares this value with the curr_deadline. If the deadline is exceeded, based on the delayed time calculates the
    penalty.

    :param available_classes: List of available classes for selected lab
    :param lab_path: Absolute file path to the lab folder containing the classes
    :param deadline: Deadline for the selected lab
    :param assign: If ture, uses assignment deadline parameters
    :return: A dictionary containing student id as key and the final submission timestamp as the value
    """

    student_num = 0
    # Extract current deadline information from the config file
    current_deadline, thresholds, penalties = get_deadline_info(deadline=deadline, assign=assign)
    submission_times, errors = get_submission_times(available_classes=available_classes, lab_path=lab_path,
                                                    print_outputs=True)
    for curr_class in available_classes:
        if curr_class.startswith("."):
            continue

        class_path = os.path.join(lab_path, curr_class)
        student_dirs = os.listdir(class_path)
        student_dirs.sort()

        for student in student_dirs:
            if student.startswith("."):
                continue

            student_num_str = str(student_num).zfill(2)
            if student in errors:
                if errors[student] == "IndexError":
                    print(f"{bcolors.OKBLUE}[{student_num_str}]{bcolors.FAIL} {curr_class} {student} "
                          f"Log file cannot be read! {bcolors.ENDC}")
                elif errors[student] == "FileNotFound":
                    print(f"{bcolors.OKBLUE}[{student_num_str}]{bcolors.WARNING} {curr_class} {student} "
                          f"Log file not found! {bcolors.ENDC}")

            elif student in submission_times:
                final_sub_time = submission_times[student]
                late_submission = current_deadline < final_sub_time

                if late_submission:
                    spacing = 5  # Defined for formatting purposes
                    delay_time = final_sub_time - current_deadline
                    penalty = calculate_late_penalty(delayed_time=delay_time, thresholds=thresholds,
                                                     penalties=penalties)
                    if penalty == -1:
                        penalty_str = 'rejected'
                    else:
                        penalty_str = f"-{str(penalty).zfill(2)}%"

                    print(f"{bcolors.OKBLUE}[{student_num_str}]{bcolors.ENDC} {bcolors.FAIL}{curr_class} {student} "
                          f"Late Sub Penalty: {f'{penalty_str}'.ljust(spacing)} {delay_time}{bcolors.ENDC}")
                else:
                    print(f"{bcolors.OKBLUE}[{student_num_str}]{bcolors.ENDC}", curr_class, student)

            student_num += 1

    return submission_times


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


def download_labs_all_classes(ssh_client: Client, term: str, lab_name: str, class_names: List[str],
                              save_path: str) -> None:
    """
    Downloads all available submissions in the list of class names given.

    :param ssh_client: A Client object with a connected SSH session
    :param term: From which term these labs should be downloaded
    :param lab_name: The lab selected
    :param class_names: The set of classes the submissions should be downloaded from
    :param save_path: The location of the local save path for the downloaded files
    :return:
    """
    for class_name in class_names:
        print(f"{bcolors.OKBLUE}Downloading {lab_name} for class: {bcolors.OKCYAN}{class_name}{bcolors.ENDC}")
        ssh_lab_path = f"/home/cs3331/{term}.work/{lab_name}/{class_name}/"
        avail_submissions = ssh_client.execute(f"ls {ssh_lab_path}")

        for submission in tqdm(avail_submissions):
            os.makedirs(os.path.join(save_path, class_name, submission), exist_ok=True)

            # Download all contents inside the folder, including subdirectories
            ssh_client.download_folder(remote_dir=os.path.join(ssh_lab_path, submission),
                                       local_dir=os.path.join(save_path, class_name, submission))


def call_download_labs(ssh_client: Client, term: str, dest_path: str, class_names: List[str]) -> None:
    """
    Connects to cse servers through SSH and downloads the submissions of all the classes defined in the config file.

    :param ssh_client: A Client object with a connected SSH session
    :param term: From which term these labs should be downloaded
    :param dest_path: The location of the local save path for the lab directory
    :param class_names: The set of classes the user teaches for that term
    """

    list_labs = f"ls /home/cs3331/{term}.work"
    avail_labs = ssh_client.execute(list_labs)
    selected_lab = get_user_selection(avail_labs)

    if check_pre_download_conditions(dest_path, selected_lab):
        download_labs_all_classes(ssh_client, term, selected_lab, class_names, os.path.join(dest_path, selected_lab))


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


def extract_all_submissions(lab_path: str) -> None:
    """
    Iterates through all student directories under all classes in a lab path and extracts the content inside the file
    'submission.tar'. Once the files are extracted, checks whether there are new .tar files created. If so, iterates
    through all the new files and untar the new .tar files.

    :param lab_path: Directory path of the lab
    :return: None
    """

    for lab_class in os.listdir(lab_path):
        # Takes care of .DStore files
        if lab_class.startswith("."):
            continue
        lab_class_path = os.path.join(lab_path, lab_class)

        for dir_path in os.listdir(lab_class_path):
            dir_path = os.path.join(lab_class_path, dir_path)
            if os.path.isdir(dir_path):
                submitted_files = os.listdir(dir_path)
                if "submission.tar" in submitted_files:
                    extract_all(os.path.join(dir_path, "submission.tar"), dir_path)


def remove_extracted(lab_path: str) -> None:
    """
    Iterates through all student directories under all classes in a lab path and removes all extracted files leaving
    out only the student submitted .tar files and the log file

    :param lab_path: Directory path of the lab
    """

    for lab_class in os.listdir(lab_path):
        # Takes care of .DStore files
        if lab_class.startswith("."):
            continue
        lab_class_path = os.path.join(lab_path, lab_class)
        for dir_path in os.listdir(lab_class_path):
            dir_path = os.path.join(lab_class_path, dir_path)
            if os.path.isdir(dir_path):
                for file_path in os.listdir(dir_path):
                    file_name, file_ext = os.path.splitext(file_path)
                    if file_name == "log":
                        continue
                    # Use regex to filter out the original .tar files (submission.tar, sub01.tar, ...)
                    elif (file_ext == ".tar" and (re.match("^sub(\d{1,3}$)", file_name))
                          or file_name == "submission" or file_name == "pre-submission"):
                        continue
                    else:
                        delete_path = os.path.join(dir_path, file_path)
                        if os.path.isdir(delete_path):
                            shutil.rmtree(delete_path)
                        else:
                            os.remove(delete_path)


def get_latest_submission_times(ssh_client: Client, term, classes, l_labs_path):
    r_all_lab_path = f"/home/cs3331/{term}.work"
    r_avail_labs = ssh_client.execute(f"ls {r_all_lab_path}")

    selected_lab = get_user_selection(r_avail_labs)
    r_lab_path = os.path.join(r_all_lab_path, selected_lab)

    r_log_paths = []
    for selected_class in classes:
        find_str = f"find {r_lab_path}/{selected_class} -type f -name log"
        r_class_log_paths = ssh_client.execute(find_str)
        if r_class_log_paths:
            r_log_paths += r_class_log_paths

    if os.path.exists(".temp"):
        shutil.rmtree(".temp")
    os.makedirs(".temp")

    student_to_class = {}
    for r_log_path in r_log_paths:
        class_name, student_id = r_log_path.split("/")[-3:-1]
        ssh_client.download_file(r_log_path, f".temp/{student_id}")
        student_to_class[student_id] = class_name

    new_sub_time = {}
    for log_file in os.listdir(".temp"):
        last_sub_time = parse_time_from_log(os.path.join(".temp", log_file))
        new_sub_time[log_file] = last_sub_time

    l_selected_lab_path = os.path.join(l_labs_path, selected_lab)
    find_str = f"find {l_selected_lab_path} -type f -name log"

    output = subprocess.check_output(find_str.split(" "))
    l_log_paths = output.decode().strip().split("\n")

    old_sub_times = {}
    for l_log_path in l_log_paths:
        student_id = l_log_path.split("/")[-2]
        old_sub_time = parse_time_from_log(l_log_path)

        old_sub_times[student_id] = old_sub_time

    updated_submissions = defaultdict(list)
    for submission in new_sub_time:
        if submission not in old_sub_times:
            record = {"zID": submission, "desc": "Found New Submission", "time": new_sub_time[submission]}
            updated_submissions[student_to_class[submission]].append(record)

        elif old_sub_times[submission] < new_sub_time[submission]:
            record = {"zID": submission, "desc": "Updated Submission", "time": new_sub_time[submission]}
            updated_submissions[student_to_class[submission]].append(record)

    print(updated_submissions)
