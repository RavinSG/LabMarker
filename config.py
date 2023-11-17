import colorlog
from dataclasses import dataclass


@dataclass
class Connection:
    host_name: str
    username: str
    private_key: str
    use_pass: bool


@dataclass
class Paths:
    known_hosts: str


@dataclass
class Config:
    connection: Connection
    paths: Paths


handler = colorlog.StreamHandler()
logger = colorlog.getLogger('Marking')
logger.setLevel("WARN")
