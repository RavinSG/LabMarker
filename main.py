import hydra

from connection.ssh import Client
from interface import actions
from config import Config, bcolors


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    print(cfg.paths.local_labs_path)
    client = None

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
            available_classes, lab_path = actions.lab_selection(local_all_labs_path=cfg.paths.local_labs_path)
            actions.check_submission_time(available_classes=available_classes, lab_path=lab_path,
                                          deadline=cfg.marking.deadline, assign=cfg.marking.assign)
        elif action == 2:
            pass
        elif action == 3:
            pass
        elif action == 4:
            pass
        elif action == 5:
            if client is None:
                client = Client(cfg)
            actions.call_download_labs(ssh_client=client, term=cfg.marking.term, dest_path=cfg.paths.local_labs_path,
                                       class_names=cfg.marking.class_names)
        else:
            break
        print("\n\n")

    if client is not None:
        client.close()
    return


if __name__ == "__main__":
    main()
