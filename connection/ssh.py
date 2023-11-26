import os
import paramiko
from getpass import getpass
from typing import List, Union
from stat import S_ISDIR, S_ISREG

from config import Config, logger


class Client:
    """
    This class is used to create an SSH connection to the server and store the connection to be used later.
    When the connection is created an SFTP client is also automatically created to transfer files between the server and
    the host.

    Supports both keys and passwords to log into the server. However, using a key is recommended.
    To connect to an SSH server it should already be in the known hosts file. Read the README file for more information.
    """
    def __init__(self, cfg: Config):
        """
        Creates a new SSH client based on the configurations provided in the config.yaml file.
        """
        self.client = paramiko.SSHClient()
        logger.info("Loading SSH known hosts")
        self.client.load_host_keys(cfg.paths.known_hosts)
        self.client.load_system_host_keys()

        if cfg.connection.use_pass:
            logger.info("Waiting for user password")
            password = getpass("Enter password: ")
            self.client.connect(
                hostname=cfg.connection.host_name,
                username=cfg.connection.username,
                password=password
            )
        else:
            try:
                logger.info("Loading private key")
                key_file = paramiko.RSAKey.from_private_key_file(cfg.connection.private_key)
            except paramiko.PasswordRequiredException:
                logger.warn("Key file requires password")
                while True:
                    logger.info("Waiting for key password")
                    try:
                        key_pass = getpass("Enter password for key file: ")
                        key_file = paramiko.RSAKey.from_private_key_file(cfg.connection.private_key, key_pass)
                        break
                    except paramiko.SSHException:
                        logger.error("Entered key password is incorrect")
                        print("The entered key pass is invalid. Please try again.")
            except FileNotFoundError:
                logger.critical("Cannot load key file")
                print("Cannot load the key file, please check the pathname")
                exit(1)
            try:
                self.client.connect(
                    hostname=cfg.connection.host_name,
                    username=cfg.connection.username,
                    pkey=key_file
                )
            except paramiko.AuthenticationException:
                logger.critical("SSH authentication failed")
                print("Authentication failed, please check whether password/key is correct.")
                exit(1)

        self.sftp_client = self.client.open_sftp()

    def execute(self, command: str) -> Union[List[str], None]:
        """
        Executes the command on the server and retrieves the output. The output is stored in a list where each line of
        the output corresponds to an element in the list.
        """

        stdin, stdout, stderr = self.client.exec_command(command)
        output = stdout.readlines()
        if output:
            output = [x.strip() for x in output]
            return output
        else:
            return None

    def download_file(self, remote_file: str, local_dest: str) -> None:
        """
        Downloads a single file from the server
        """

        self.sftp_client.get(remote_file, local_dest)

    def download_folder(self, remote_dir: str, local_dir: str) -> None:
        """
        Paramiko doesn't support downloading folders. Hence, this function checks whether there are directories in the
        remote_dir and calls itself for each folder to download the content inside.

        :param remote_dir: Location of the directory to be downloaded on the server
        :param local_dir: Location where the downloaded directory should be saved
        """

        for entry in self.sftp_client.listdir_attr(remote_dir):
            remote_path = os.path.join(remote_dir, entry.filename)
            local_path = os.path.join(local_dir, entry.filename)
            mode = entry.st_mode

            if S_ISDIR(mode):
                try:
                    os.mkdir(local_path)
                except OSError:
                    pass
                self.download_folder(remote_path, local_path)
            elif S_ISREG(mode):
                self.sftp_client.get(remote_path, local_path)

    def close(self) -> None:
        """
        Closes the client and the sftp connection to release resources
        """

        self.sftp_client.close()
        self.client.close()
