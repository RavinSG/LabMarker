import os
import tarfile
from typing import List

from config import bcolors
from datetime import datetime


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
