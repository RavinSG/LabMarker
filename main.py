import hydra

from connection.ssh import Client
from interface import actions
from config import Config, bcolors


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    print(cfg.paths.lab_save_path)
    client = Client(cfg)
    client.execute("pwd")
    client.execute("ls")

    while True:
        action = input(
            f"Select action: \n \t\t "
            f"[1] Check submission times\n \t\t "
            f"[2] Compare two labs\n \t\t "
            f"[3] Extract all submissions \n \t\t "
            f"[4] Remove extracted \n \t\t "
            f"[5] Download labs through SSH \n \t\t "
            f"\n{bcolors.OKBLUE}Action: {bcolors.ENDC}")
        action = int(action)
        if action == 1:
            pass
        elif action == 2:
            pass
        elif action == 3:
            pass
        elif action == 4:
            pass
        elif action == 5:
            actions.call_download_labs(ssh_client=client, term=cfg.marking.term, dest_path=cfg.paths.lab_save_path,
                                       class_names=cfg.marking.class_names)
        else:
            break
        print("\n\n")

    client.close()
    return


if __name__ == "__main__":
    main()
