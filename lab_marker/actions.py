import os
import re
import shutil

from datetime import datetime
from collections import defaultdict
from typing import List, Tuple, Dict, Union
from tqdm import tqdm

from config import bcolors, Config
from connection.ssh import Client
from lab_marker import remote, utils
from lab_marker import file_handler
from lab_marker.auto.lab2.marker import mark_lab_2


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
        lab_num = utils.print_and_get_selection(selection_list=avail_labs)

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

        file_handler.clean_dir(dir_path=".temp")

        # Get the paths of the log files relevant to the classes for the selected lab
        r_log_paths, selected_lab = remote.get_log_paths(ssh_client=self.ssh_client, term=self.marking.term,
                                                         classes=self.marking.class_names)

        # Download the log files for the selected lab from the remote server
        r_submissions = remote.download_log_files(ssh_client=self.ssh_client, r_log_paths=r_log_paths,
                                                  selected_lab=selected_lab)

        # Extract the submissions times from the downloaded log files
        new_sub_time = {}
        for log_file in os.listdir(".temp"):
            last_sub_time = file_handler.parse_time_from_log(os.path.join(".temp", log_file))
            new_sub_time[log_file] = last_sub_time

        # Local lab path should be a subdirectory inside the all labs directory
        l_selected_lab_path = os.path.join(self.paths.local_labs_path, selected_lab)
        l_lab_classes = os.listdir(l_selected_lab_path)

        # Get the last submission times from the downloaded lab
        old_sub_times, _ = file_handler.get_submission_times(available_classes=l_lab_classes,
                                                             lab_path=l_selected_lab_path)

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
            lab_class = r_submissions[submission].lab_class
            updated_submissions[lab_class].append(record)
            new_sub_count += 1

        print(f"\nFound {bcolors.FAIL}{new_sub_count}{bcolors.ENDC} new submission(s)")

        # Print out the new submissions found
        for lab_class in updated_submissions.keys():
            for submission_record in updated_submissions[lab_class]:
                print(f'{bcolors.OKCYAN}[{lab_class}]{bcolors.ENDC} {submission_record["zID"]} {bcolors.WARNING} '
                      f'{submission_record["desc"]} {submission_record["time"]}{bcolors.ENDC}')

        if updated_submissions:
            download_new = input(
                f"\nDo you want to download all updated/new submissions {bcolors.OKBLUE}y/[n]?{bcolors.ENDC}")

            if download_new.lower() == "y":
                download_list = []

                # Combine new submissions from all classes to a single list
                for value in updated_submissions.values():
                    download_list += value

                source_paths = [r_submissions[x['zID']].r_path for x in download_list]
                # Generate the destination path for each submission based on the folder structure
                destination_paths = [os.path.join(self.paths.local_labs_path, r_submissions[x['zID']].lab,
                                                  r_submissions[x['zID']].lab_class, x['zID']) for x in download_list]

                remote.download_selected(ssh_client=self.ssh_client, remote_paths=source_paths,
                                         local_paths=destination_paths)

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
            lab_classes = tqdm(os.listdir(lab_class_path))

            for dir_path in lab_classes:
                lab_classes.set_description(f"Extracting submissions for {lab_class}")
                dir_path = os.path.join(lab_class_path, dir_path)
                if os.path.isdir(dir_path):
                    submitted_files = os.listdir(dir_path)

                    # Select the submission.tar file inside the student directory
                    if "submission.tar" in submitted_files:
                        file_handler.extract_all(tar_file_path=os.path.join(dir_path, "submission.tar"),
                                                 extract_path=dir_path)

    def remove_extracted(self) -> None:
        """
        Iterates through all student directories under all classes in a lab path and removes all extracted files leaving
        out only the student submitted .tar files and the log file
        """

        _, lab_path_to_clear = self.lab_selection()

        print(f"{bcolors.FAIL}Deleting extracted files from submissions{bcolors.ENDC}")
        file_count = 0
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
                                file_count += 1
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
        selected_lab_num = utils.print_and_get_selection(avail_labs)
        selected_lab = avail_labs[selected_lab_num]

        # Before downloading, check whether there is an existing lab downloaded before
        if file_handler.check_pre_download_conditions(destination_path=self.paths.local_labs_path,
                                                      lab_name=selected_lab):
            remote.download_labs_all_classes(ssh_client=self.ssh_client,
                                             term=self.marking.term,
                                             lab_name=selected_lab,
                                             class_names=self.marking.class_names,
                                             save_path=os.path.join(self.paths.local_labs_path, selected_lab))

    def mark_lab_2(self):

        avail_classes = None

        while True:
            lab2_path = os.path.join(self.paths.local_labs_path, 'Lab2')

            if not os.path.exists(lab2_path):
                user_input = input("Could not find Lab2 directory. [S]elect manually, [D]ownload from server, [Q]uit")

                if user_input.upper() == 'S':
                    avail_classes, lab2_path = self.lab_selection()
                    break

                elif user_input.upper() == 'D':
                    self.download_labs()

            else:
                break

        if avail_classes is None:
            avail_classes = [x for x in os.listdir(lab2_path) if not x.startswith('.')]

        individual = input("Do you want to mark them individually? yes, [N]o")

        if individual.upper() == 'N':
            for avail_class in avail_classes:
                print(f"Marking submissions of {avail_class}")
                out_path = os.path.join(self.paths.auto_outputs_dir, 'lab2', avail_class)

                class_path = os.path.join(lab2_path, avail_class)
                mark_lab_2(class_path=class_path, output_destination=out_path)
        else:
            utils.print_and_get_selection(avail_classes, selection_type='class')
