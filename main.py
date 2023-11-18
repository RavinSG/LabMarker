import hydra

from config import Config
from connection.ssh import Client


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    client = Client(cfg)
    client.close()
    return


if __name__ == "__main__":
    main()
