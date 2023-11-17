from paramiko import SSHClient

from config import Config


class Client:
    def __init__(self, cfg: Config, password=None):
        self.client = SSHClient()

        self.client.load_host_keys(cfg.paths.known_hosts)
        self.client.load_system_host_keys()

        if cfg.connection.use_pass:
            self.client.connect(
                hostname=cfg.connection.host_name,
                username=cfg.connection.username,
                password=password
            )
        else:
            self.client.connect(
                hostname=cfg.connection.host_name,
                username=cfg.connection.username,
                key_filename=cfg.connection.private_key
            )

        stdin, stdout, stderr = self.client.exec_command('ls')
        print(stdout.readlines())

    def close(self):
        self.client.close()
