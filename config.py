import colorlog
import logging
from enum import Enum
from typing import List
from dataclasses import dataclass


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@dataclass
class Connection:
    host_name: str
    username: str
    private_key: str
    use_pass: bool


@dataclass
class Paths:
    known_hosts: str
    local_labs_path: str
    auto_outputs_dir: str


@dataclass
class Deadline:
    cur: str
    thresholds: List[int]
    lab_penalties: List[int]
    assign_penalties: List[int]


@dataclass
class Marking:
    term: str
    class_names: List[str]
    assign: bool
    deadline: Deadline


@dataclass
class Config:
    connection: Connection
    paths: Paths
    marking: Marking


@dataclass
class RemoteSubmission:
    zID: str
    r_path: str
    lab: str
    lab_class: str


class ExecStatus(Enum):
    OK = 0
    EXECUTION_FAILED = -1
    FILE_NOT_FOUND = -2
    UNEXPECTED_TERMINATION = -3

    @staticmethod
    def get_description(item):
        status_descriptions = {
            0: "Process executed correctly",
            -1: "Could not execute process",
            -2: "File not found",
            -3: "Process terminated unexpectedly"
        }

        if item not in status_descriptions.keys():
            return "Return status not defined"

        return status_descriptions[item]


file_handler = logging.FileHandler('main.log', mode='w')
file_formatter = logging.Formatter('%(levelname)-8s %(asctime)s:%(name)s:%(message)s')
file_handler.setFormatter(file_formatter)

logger = colorlog.getLogger('Marking')
logger.addHandler(file_handler)
