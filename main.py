import hydra

from config import Config, bcolors
from lab_marker.actions import Actions


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    actions = Actions(cfg)

    while True:
        action = input(
            f"Select action: \n \t\t "
            f"[1] Check submission times\n \t\t "
            f"[2] Check for new submissions\n \t\t "
            f"[3] Extract all submissions \n \t\t "
            f"[4] Remove extracted \n \t\t "
            f"[5] Download labs through SSH \n \t\t "
            f"[6] Auto mark Lab 2 (PingClient) \n \t\t "
            f"\n{bcolors.OKBLUE}Action: {bcolors.ENDC}")

        action = int(action)
        if action == 1:
            actions.check_late_submissions()

        elif action == 2:
            actions.check_new_submissions()

        elif action == 3:
            actions.extract_all_submissions()

        elif action == 4:
            actions.remove_extracted()

        elif action == 5:
            actions.download_labs()

        elif action == 6:
            actions.mark_lab_2()

        else:
            break
        print("\n\n")

    actions.close()

    return


if __name__ == "__main__":
    main()
