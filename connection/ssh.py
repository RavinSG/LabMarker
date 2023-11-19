import os
import paramiko
from getpass import getpass
from stat import S_ISDIR, S_ISREG

from config import Config, logger


class Client:
    def __init__(self, cfg: Config):
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

    def execute(self, command: str):
        stdin, stdout, stderr = self.client.exec_command(command)
        output = stdout.readlines()
        if output:
            output = [x.strip() for x in output]
            return output
        else:
            return None

    # Paramiko doesn't support recursive download, need to implement it manually
    def download_folder(self, remote_dir, local_dir):
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

    def close(self):
        self.sftp_client.close()
        self.client.close()
