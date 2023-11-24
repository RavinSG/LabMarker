import os
from tqdm import tqdm
from typing import List

from config import bcolors
from connection.ssh import Client
from interface import utils


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


def get_log_paths(ssh_client: Client, term, classes):
    r_all_lab_path = f"/home/cs3331/{term}.work"
    r_avail_labs = ssh_client.execute(f"ls {r_all_lab_path}")

    selected_lab = utils.get_user_selection(r_avail_labs)
    r_lab_path = os.path.join(r_all_lab_path, selected_lab)

    r_log_paths = []
    for selected_class in classes:
        find_str = f"find {r_lab_path}/{selected_class} -type f -name log"
        r_class_log_paths = ssh_client.execute(find_str)
        if r_class_log_paths:
            r_log_paths += r_class_log_paths

    return r_log_paths, selected_lab
