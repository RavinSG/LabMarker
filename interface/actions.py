import os
import shutil
from typing import List, Tuple
from tqdm import tqdm
from datetime import datetime

from connection.ssh import Client
from config import bcolors


def print_and_get_sub_selection(lab_names: List[str]) -> int:
    lab_names.sort()

    for i, lab in enumerate(lab_names):
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

    avail_classes = os.listdir(os.path.join(local_all_labs_path, avail_labs[lab_num]))
    lab_path = os.path.join(local_all_labs_path, avail_labs[lab_num])

    return avail_classes, lab_path

def check_pre_download_conditions(destination_path: str, lab_name: str) -> bool:
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
                to_be_moved_dirs = []
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


def get_user_selection(available_options: List[str], selection_type: str = "Labs") -> str:
    """
    Given a list of lab names, print them to the console in a user-friendly format and waits for the user to make a
    selection. The selection is validated against non-integer and out of range inputs.

    :param selection_type:
    :param available_options: A list of labs
    :return: Name on the user selected lab
    """
    singular = {
        "Labs": "Lab",
        "Classes": "Class"
    }

    print(f"{bcolors.OKCYAN}Available {selection_type}:{bcolors.ENDC}")
    for i, lab in enumerate(available_options):
        print(f"{bcolors.OKBLUE}[{i}]{bcolors.ENDC}", lab)

    while True:
        selected_option = input(
            f"{bcolors.OKGREEN}\nSelect your {singular[selection_type]} w/o brackets: {bcolors.ENDC}")

        try:
            selected_option = int(selected_option)
        except ValueError:
            print(f"{bcolors.FAIL}Please enter a valid number{bcolors.ENDC}")
            continue

        if selected_option >= len(available_options) or selected_option < 0:
            print(f"{bcolors.FAIL}{singular[selection_type]} not found{bcolors.ENDC}")
        else:
            break

    return available_options[selected_option]


def download_labs_all_classes(ssh_client: Client, term: str, lab_name: str, class_names: List[str], save_path: str):
    for class_name in class_names:
        print(f"{bcolors.OKBLUE}Downloading {lab_name} for class: {bcolors.OKCYAN}{class_name}{bcolors.ENDC}")
        ssh_lab_path = f"/home/cs3331/{term}.work/{lab_name}/{class_name}/"
        avail_submissions = ssh_client.execute(f"ls {ssh_lab_path}")

        for submission in tqdm(avail_submissions):
            os.makedirs(os.path.join(save_path, class_name, submission), exist_ok=True)
            ssh_client.download_folder(remote_dir=os.path.join(ssh_lab_path, submission),
                                       local_dir=os.path.join(save_path, class_name, submission))


def call_download_labs(ssh_client: Client, term: str, dest_path: str, class_names: List[str]):
    list_labs = f"ls /home/cs3331/{term}.work"
    avail_labs = ssh_client.execute(list_labs)
    selected_lab = get_user_selection(avail_labs, "Labs")

    if check_pre_download_conditions(dest_path, selected_lab):
        download_labs_all_classes(ssh_client, term, selected_lab, class_names, os.path.join(dest_path, selected_lab))
