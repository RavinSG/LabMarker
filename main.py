import hydra
from getpass import getpass

from config import Config
from connection.ssh import Client


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    if cfg.connection.use_pass:
        password = getpass("Enter password: ")
        client = Client(cfg, password=password)

    else:
        client = Client(cfg)

    client.close()
    return


if __name__ == "__main__":
    main()
