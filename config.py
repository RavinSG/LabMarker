import colorlog
import logging
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
    lab_save_path: str


@dataclass
class Marking:
    term: str
    class_names: List[str]


@dataclass
class Config:
    connection: Connection
    paths: Paths
    marking: Marking


file_handler = logging.FileHandler('main.log', mode='w')
file_formatter = logging.Formatter('%(levelname)-8s %(asctime)s:%(name)s:%(message)s')
file_handler.setFormatter(file_formatter)

logger = colorlog.getLogger('Marking')
logger.addHandler(file_handler)
