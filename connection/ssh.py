import paramiko
from getpass import getpass

from config import Config


class Client:
    def __init__(self, cfg: Config):
        self.client = paramiko.SSHClient()

        self.client.load_host_keys(cfg.paths.known_hosts)
        self.client.load_system_host_keys()

        if cfg.connection.use_pass:
            password = getpass("Enter password: ")
            self.client.connect(
                hostname=cfg.connection.host_name,
                username=cfg.connection.username,
                password=password
            )
        else:
            try:
                key_file = paramiko.RSAKey.from_private_key_file(cfg.connection.private_key)
            except paramiko.PasswordRequiredException:
                while True:
                    try:
                        key_pass = getpass("Enter password for key file: ")
                        key_file = paramiko.RSAKey.from_private_key_file(cfg.connection.private_key, key_pass)
                        break
                    except paramiko.SSHException:
                        print("The entered key pass is invalid. Please try again.")

            try:
                self.client.connect(
                    hostname=cfg.connection.host_name,
                    username=cfg.connection.username,
                    pkey=key_file
                )
            except paramiko.AuthenticationException:
                print("Authentication failed, please check whether password/key is correct.")
                exit(1)

        stdin, stdout, stderr = self.client.exec_command('ls')
        print(stdout.readlines())

    def close(self):
        self.client.close()
