from typing import List, Tuple

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


def print_and_get_selection(selection_list: List[str], selection_type="lab") -> int:
    """
    Print all the selections in the list to the terminal with the corresponding index. Then waits for the user input to
    make a selection based on the index. Returns the selected index to the calling function. Performs basic input
    verification.

    :param selection_list: A list of selection names as strings
    :param selection_type: The type of selection (lab/class/submission)
    :return: The index of the selected lab
    """

    selection_list.sort()

    for i, selection in enumerate(selection_list):
        # Ignore folders that are hidden
        if not selection.startswith("."):
            print(f"{bcolors.OKBLUE}[{i}]{bcolors.ENDC}", selection)

    while True:
        selection_num = input(f"\nEnter {selection_type} number w/o brackets: ")

        try:
            selection_num = int(selection_num)
        except ValueError:
            print(f"{bcolors.FAIL}Please enter a valid number{bcolors.ENDC}")
            continue

        if selection_num >= len(selection_list) or selection_num < 0:
            print(f"{bcolors.FAIL}{selection_type.title()} not found{bcolors.ENDC}")
        else:
            return selection_num


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
