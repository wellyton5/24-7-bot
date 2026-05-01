import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def find_file_recursive():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    target = "truck_availability.json"

    def walk(path):
        print(f"Checking {path}...")
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            if target in items:
                print(f"\n[FOUND] {path}/{target}\n")
                return True

            # Recurse into directories
            for item in items:
                if "." not in item:  # Simple check for directory
                    if walk(f"{path}/{item}".replace("//", "/")):
                        return True
        except:
            pass
        return False

    # Check common locations first
    search_paths = ["/profile", "/dayzxb", "/dayzxb/config", "/"]
    for p in search_paths:
        if walk(p):
            break

    ftp.quit()


if __name__ == "__main__":
    find_file_recursive()
