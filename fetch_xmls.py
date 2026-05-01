import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

MISSION_PATH = "/dayzxb_missions/dayzOffline.chernarusplus"


def fetch_xmls():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        # Corrected paths based on LIST output
        targets = [
            ("db/events.xml", "events.xml.bak"),
            ("env/wolf_territories.xml", "wolf_territories.xml.bak"),
        ]

        for remote, local in targets:
            print(f"Downloading {remote}...")
            with open(f"/home/ubuntu/24-7-Bot/backups/{local}", "wb") as f:
                ftp.retrbinary(f"RETR {MISSION_PATH}/{remote}", f.write)

        ftp.quit()
        print("XML backups complete.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if not os.path.exists("/home/ubuntu/24-7-Bot/backups"):
        os.makedirs("/home/ubuntu/24-7-Bot/backups")
    fetch_xmls()
