import os
import shutil
import tarfile
from datetime import datetime
from typing import List, Dict, Tuple

from config import bcolors


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
    except IsADirectoryError:
        print(tar_file_path, "File is a directory")


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
        os.makedirs(lab_path)
        return True


def clean_dir(dir_path):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)

    os.makedirs(dir_path)
