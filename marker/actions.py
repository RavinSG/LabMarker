import os
import re
import shutil
import subprocess

from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
from typing import List, Tuple, Dict, Union

from config import bcolors, Config, RemoteSubmission
from connection.ssh import Client
from marker import remote, utils
from marker import file_handler


class Actions:
    """
    This class contains the actions a user can execute from the terminal when the program is run.
    """

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
        lab_num = utils.print_and_get_sub_selection(avail_labs)

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
        current_deadline, thresholds, penalties = utils.get_deadline_info(deadline=self.marking.deadline,
                                                                          assign=self.marking.assign)

        # Create a dictionary containing the final submission times of the students
        submission_times, errors = file_handler.get_submission_times(available_classes=available_classes,
                                                                     lab_path=lab_path)
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
                        penalty = utils.calculate_late_penalty(delayed_time=delay_time, thresholds=thresholds,
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

    def check_new_submissions(self) -> None:
        """
        Check whether there are updated or new submissions since the last download of a lab. If there are, the updated
        submissions are printed to the console.
        """

        if self.ssh_client is None:
            self.ssh_client = Client(self.cfg)

        if os.path.exists(".temp"):
            shutil.rmtree(".temp")
        os.makedirs(".temp")

        # Get the paths of the log files relevant to the classes for the selected lab
        r_log_paths, selected_lab = remote.get_log_paths(self.ssh_client, self.marking.term, self.marking.class_names)

        # Store a mapping of student id to submission record for future references
        r_submissions: Dict[str, RemoteSubmission] = {}

        for r_log_path in tqdm(r_log_paths, desc="Reading remote log files"):
            class_name, student_id = r_log_path.split("/")[-3:-1]
            r_submission_path = "/".join(r_log_path.split("/")[:-1])
            r_submission = RemoteSubmission(zID=student_id, r_path=r_submission_path,
                                            lab=selected_lab, lab_class=class_name)

            # Download and save the log files in a temporary directory
            self.ssh_client.download_file(r_log_path, f".temp/{student_id}")
            r_submissions[student_id] = r_submission

        # Extract the submissions times from the downloaded log files
        new_sub_time = {}
        for log_file in os.listdir(".temp"):
            last_sub_time = file_handler.parse_time_from_log(os.path.join(".temp", log_file))
            new_sub_time[log_file] = last_sub_time

        # Local lab path should be a subdirectory inside the all labs directory
        l_selected_lab_path = os.path.join(self.paths.local_labs_path, selected_lab)
        find_str = f"find {l_selected_lab_path} -type f -name log"

        output = subprocess.check_output(find_str.split(" "))
        l_log_paths = output.decode().strip().split("\n")
        old_sub_times = {}

        # Iterate through log files in the locally downloaded lab and extract last submission times
        for l_log_path in l_log_paths:
            student_id = l_log_path.split("/")[-2]
            old_sub_time = file_handler.parse_time_from_log(l_log_path)
            old_sub_times[student_id] = old_sub_time

        updated_submissions = defaultdict(list)
        new_sub_count = 0

        # Iterate through the new submissions since it has the updated submission list
        for submission in new_sub_time:
            if submission not in old_sub_times:
                desc = "Found New Submission"
            elif old_sub_times[submission] < new_sub_time[submission]:
                desc = "Updated Submission"
            else:
                continue

            record = {"zID": submission, "desc": desc, "time": new_sub_time[submission]}
            updated_submissions[r_submissions[submission].lab_class].append(record)
            new_sub_count += 1

        print(f"\nFound {bcolors.FAIL}{new_sub_count}{bcolors.ENDC} new submission(s)")

        # Print out the new submissions found
        for lab_class in updated_submissions.keys():
            for submission_record in updated_submissions[lab_class]:
                print(f'{bcolors.OKCYAN}[{lab_class}]{bcolors.ENDC} {submission_record["zID"]} {bcolors.WARNING} '
                      f'{submission_record["desc"]}{bcolors.ENDC}')

        download_new = input(
            f"Do you want to download all updated/new submissions {bcolors.OKBLUE}y/[n]?{bcolors.ENDC}")

        if download_new.lower() == "y":
            download_list = []

            # Combine new submissions from all classes to a single list
            for value in updated_submissions.values():
                download_list += value

            source_paths = [r_submissions[x['zID']].r_path for x in download_list]
            # Generate the destination path for each submission based on the folder structure
            destination_paths = [os.path.join(self.paths.local_labs_path, r_submissions[x['zID']].lab,
                                              r_submissions[x['zID']].lab_class, x['zID']) for x in download_list]
            remote.download_selected(self.ssh_client, source_paths, destination_paths)

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
                        file_handler.extract_all(os.path.join(dir_path, "submission.tar"), dir_path)

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
        if file_handler.check_pre_download_conditions(self.paths.local_labs_path, selected_lab):
            remote.download_labs_all_classes(self.ssh_client, self.marking.term, selected_lab, self.marking.class_names,
                                             os.path.join(self.paths.local_labs_path, selected_lab))
