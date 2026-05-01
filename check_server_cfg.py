import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def check_cfg():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        # Look for serverDZ.cfg in root
        files = ftp.nlst()
        cfg_file = "serverDZ.cfg"
        if cfg_file in files:
            print(f"Reading {cfg_file}...")
            lines = []
            ftp.retrlines(f"RETR {cfg_file}", lines.append)
            content = "\n".join(lines)
            if "enableCfgGameplayFile" in content:
                print("Found enableCfgGameplayFile setting.")
                for line in lines:
                    if "enableCfgGameplayFile" in line:
                        print(f"Setting: {line.strip()}")
            else:
                print("enableCfgGameplayFile NOT found in serverDZ.cfg")
        else:
            print("serverDZ.cfg not found in root.")

        ftp.quit()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_cfg()
