import os
import re
import shutil
import subprocess

from typing import List, Tuple, Dict, Union
from datetime import datetime, timedelta
from collections import defaultdict

from config import bcolors, Deadline, Config
from connection.ssh import Client
from interface import remote, utils


class Actions:
    def __init__(self, cfg: Config, out_stream=None):
        self.out_stream = out_stream
        self.ssh_client: Union[Client, None] = None

        self.cfg = cfg
        self.paths = cfg.paths
        self.marking = cfg.marking

    def write_to_out_stream(self, message):
        if self.out_stream is None:
            print(message)

    def close(self):
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

    def lab_selection(self) -> Tuple[List[str], str]:
        """
        Lists down all available labs in the local download path and prompts the user to pick a specific lab number.
        If the input lab number is present, returns all class names under the given lab and their respective directory
        paths

        :return: The available class names (eg: 'fri09-oboe') in the lab and the path of the lab directory
        """

        avail_labs = os.listdir(self.paths.local_labs_path)
        lab_num = print_and_get_sub_selection(avail_labs)

        lab_path = os.path.join(self.paths.local_labs_path, avail_labs[lab_num])
        avail_classes = os.listdir(lab_path)

        return avail_classes, lab_path

    def check_late_submissions(self) -> Dict[str, datetime]:
        """
        Prompts the user to select a lab from the downloaded labs. After selecting a lab, uses the available classes
        for that lab and the lab path to check the time of the last submission for each student. Opens the log file of
        each submission and reads the final line to get the last submitted time. Then compares this value with the
        curr_deadline. If the deadline is exceeded, based on the delayed time calculates the penalty.

        :return: A dictionary containing student id as key and the final submission timestamp as the value
        """

        student_num = 0
        available_classes, lab_path = self.lab_selection()

        # Extract current deadline information from the config file
        current_deadline, thresholds, penalties = get_deadline_info(deadline=self.marking.deadline,
                                                                    assign=self.marking.assign)

        # Create a dictionary containing the final submission times of the students
        submission_times, errors = get_submission_times(available_classes=available_classes, lab_path=lab_path)
        for curr_class in available_classes:
            if curr_class.startswith("."):
                continue

            class_path = os.path.join(lab_path, curr_class)
            student_dirs = os.listdir(class_path)
            student_dirs.sort()

            for student in student_dirs:
                if student.startswith("."):
                    continue

                student_num_str = str(student_num).zfill(2)  # Formatting for printing to the terminal
                if student in errors:
                    # Checks whether the logfile is empty
                    if errors[student] == "IndexError":
                        print(f"{bcolors.OKBLUE}[{student_num_str}]{bcolors.FAIL} {curr_class} {student} "
                              f"Log file cannot be read! {bcolors.ENDC}")

                    # Checks whether the logfile is missing
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
                        # If there are no issues with the logfile and the deadline is not exceeded just print the zID
                        print(f"{bcolors.OKBLUE}[{student_num_str}]{bcolors.ENDC}", curr_class, student)

                student_num += 1

        return submission_times

    # TODO: Add functionality to download the updated submissions
    def check_new_submissions(self) -> None:
        """
        Check whether there are updated or new submissions since the last download of a lab. If there are, the updated
        submissions are printed to the console.
        """

        if self.ssh_client is None:
            self.ssh_client = Client(self.cfg)

        r_log_paths, selected_lab = remote.get_log_paths(self.ssh_client, self.marking.term, self.marking.class_names)

        if os.path.exists(".temp"):
            shutil.rmtree(".temp")
        os.makedirs(".temp")

        student_to_class = {}
        for r_log_path in r_log_paths:
            class_name, student_id = r_log_path.split("/")[-3:-1]
            self.ssh_client.download_file(r_log_path, f".temp/{student_id}")
            student_to_class[student_id] = class_name

        new_sub_time = {}
        for log_file in os.listdir(".temp"):
            last_sub_time = utils.parse_time_from_log(os.path.join(".temp", log_file))
            new_sub_time[log_file] = last_sub_time

        l_selected_lab_path = os.path.join(self.paths.local_labs_path, selected_lab)
        find_str = f"find {l_selected_lab_path} -type f -name log"

        output = subprocess.check_output(find_str.split(" "))
        l_log_paths = output.decode().strip().split("\n")

        old_sub_times = {}
        for l_log_path in l_log_paths:
            student_id = l_log_path.split("/")[-2]
            old_sub_time = utils.parse_time_from_log(l_log_path)

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

    def extract_all_submissions(self) -> None:
        """
        Iterates through all student directories in a lab directory and extracts the content inside the file
        'submission.tar'. Once the files are extracted, checks whether there are new .tar files created. If so, iterates
         through all the new files and untar the new .tar files.
        """

        # Get the path of the lab that nees to be extracted
        _, extract_lab_path = self.lab_selection()

        for lab_class in os.listdir(extract_lab_path):
            # Takes care of .DStore files
            if lab_class.startswith("."):
                continue
            lab_class_path = os.path.join(extract_lab_path, lab_class)

            for dir_path in os.listdir(lab_class_path):
                dir_path = os.path.join(lab_class_path, dir_path)
                if os.path.isdir(dir_path):
                    submitted_files = os.listdir(dir_path)

                    # Select the submission.tar file inside the student directory
                    if "submission.tar" in submitted_files:
                        utils.extract_all(os.path.join(dir_path, "submission.tar"), dir_path)

    def remove_extracted(self) -> None:
        """
        Iterates through all student directories under all classes in a lab path and removes all extracted files leaving
        out only the student submitted .tar files and the log file
        """

        _, lab_path_to_clear = self.lab_selection()

        for lab_class in os.listdir(lab_path_to_clear):
            # Takes care of .DStore files
            if lab_class.startswith("."):
                continue

            lab_class_path = os.path.join(lab_path_to_clear, lab_class)
            for student_dir_path in os.listdir(lab_class_path):
                student_dir_path = os.path.join(lab_class_path, student_dir_path)

                if os.path.isdir(student_dir_path):
                    for file_path in os.listdir(student_dir_path):
                        file_name, file_ext = os.path.splitext(file_path)

                        if file_name == "log":
                            continue

                        # Use regex to filter out the original .tar files (submission.tar, sub01.tar, ...)
                        elif (file_ext == ".tar" and (re.match("^sub(\d{1,3}$)", file_name))
                              or file_name == "submission" or file_name == "pre-submission"):
                            continue

                        else:
                            delete_path = os.path.join(student_dir_path, file_path)
                            if os.path.isdir(delete_path):
                                shutil.rmtree(delete_path)

                            else:
                                os.remove(delete_path)

    def download_labs(self) -> None:
        """
        Connects to cse servers through SSH and downloads the submissions of all the classes defined in the config file.
        """
        if self.ssh_client is None:
            self.ssh_client = Client(self.cfg)

        list_labs = f"ls /home/cs3331/{self.marking.term}.work"
        # Get the available labs from the CSE server
        avail_labs = self.ssh_client.execute(list_labs)
        selected_lab = utils.get_user_selection(avail_labs)

        # Before downloading, check whether there is an existing lab downloaded before
        if check_pre_download_conditions(self.paths.local_labs_path, selected_lab):
            remote.download_labs_all_classes(self.ssh_client, self.marking.term, selected_lab, self.marking.class_names,
                                             os.path.join(self.paths.local_labs_path, selected_lab))


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
                submission_times[student_dir] = utils.parse_time_from_log(log_path)

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
