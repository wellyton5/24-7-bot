import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def list_all_dirs():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    dirs = []

    def walk(path):
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                # Basic check for directory: no extension or it's 'db', 'missions', etc.
                if "." not in item or item in [
                    "db",
                    "missions",
                    "config",
                    "Users",
                    "Server",
                ]:
                    full_path = f"{path}/{item}".replace("//", "/")
                    dirs.append(full_path)
                    print(f"Found Dir: {full_path}")
        except:
            pass

    # Start from root
    walk("/")

    # Check one level deeper for promising ones
    current_dirs = list(dirs)
    for d in current_dirs:
        walk(d)

    ftp.quit()
    print("\n--- Final Directory List ---")
    for d in sorted(list(set(dirs))):
        print(d)


if __name__ == "__main__":
    list_all_dirs()
