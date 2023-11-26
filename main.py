import hydra

from interface.actions import Actions
from config import Config, bcolors


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    client = None
    marking_actions = Actions(cfg)

    while True:
        action = input(
            f"Select action: \n \t\t "
            f"[1] Check submission times\n \t\t "
            f"[2] Check for new submissions\n \t\t "
            f"[3] Extract all submissions \n \t\t "
            f"[4] Remove extracted \n \t\t "
            f"[5] Download labs through SSH \n \t\t "
            f"\n{bcolors.OKBLUE}Action: {bcolors.ENDC}")

        action = int(action)
        if action == 1:
            marking_actions.check_late_submissions()

        elif action == 2:
            marking_actions.check_new_submissions()

        elif action == 3:
            marking_actions.extract_all_submissions()

        elif action == 4:
            marking_actions.remove_extracted()

        elif action == 5:
            marking_actions.download_labs()

        else:
            break
        print("\n\n")

    if client is not None:
        client.close()
    return


if __name__ == "__main__":
    main()
