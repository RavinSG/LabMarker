import paramiko
from getpass import getpass

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

    def execute(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        print(stdout.readlines())

    def close(self):
        self.client.close()
