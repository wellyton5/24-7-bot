import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def find_cfg():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        print("Searching for serverDZ.cfg...")
        # Check root
        root_files = ftp.nlst()
        print(f"Root files: {root_files}")

        # Check standard Nitrado paths
        paths = ["/", "/dayzxb/", "/config/"]
        for path in paths:
            try:
                ftp.cwd(path)
                print(f"Checking {path}: {ftp.nlst()}")
                if "serverDZ.cfg" in ftp.nlst():
                    print(f"!!! Found serverDZ.cfg in {path} !!!")
                    lines = []
                    ftp.retrlines("RETR serverDZ.cfg", lines.append)
                    for line in lines:
                        if "enableCfgGameplayFile" in line:
                            print(f"Setting: {line.strip()}")
            except:
                continue

        ftp.quit()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    find_cfg()
