import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def explore_ftp():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    paths_to_check = ["/profile", "/dayzxb/config", "/dayzxb"]

    for path in paths_to_check:
        print(f"\n--- EXPLORANDO: {path} ---")
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                print(f"  [FILE/DIR] {item}")
                if "truck" in item.lower():
                    print(f"    !!! ENCONTRADO: {item}")
        except Exception as e:
            print(f"  [ERRO] {e}")

    ftp.quit()


if __name__ == "__main__":
    explore_ftp()
