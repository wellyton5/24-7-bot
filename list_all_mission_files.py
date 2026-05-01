import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def list_all_mission_files():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    def list_recursive(current_path):
        print(f"\nConteúdo de {current_path}:")
        ftp.cwd(current_path)
        items = ftp.nlst()
        for item in items:
            if "." in item:
                print(f"  [FILE] {item}")
            else:
                print(f"  [DIR]  {item}")
                try:
                    list_recursive(f"{current_path}/{item}")
                    ftp.cwd("..")
                except:
                    pass

    list_recursive(path)
    ftp.quit()


if __name__ == "__main__":
    list_all_mission_files()
