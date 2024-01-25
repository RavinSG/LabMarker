import hydra

from lab_marker.actions import Actions
from config import Config, bcolors


@hydra.main(config_path='.', config_name="config.yaml", version_base=None)
def main(cfg: Config):
    marker = Actions(cfg)

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
            marker.check_late_submissions()

        elif action == 2:
            marker.check_new_submissions()

        elif action == 3:
            marker.extract_all_submissions()

        elif action == 4:
            marker.remove_extracted()

        elif action == 5:
            marker.download_labs()

        elif action == 6:
            marker.mark_lab_2()

        else:
            break
        print("\n\n")

    marker.close()

    return


if __name__ == "__main__":
    main()
