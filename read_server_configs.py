import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def read_configs():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        files = [
            "/dayzxb_missions/dayzOffline.chernarusplus/cfgweather.xml",
            "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json",
            "/dayzxb_missions/dayzOffline.chernarusplus/init.c",
        ]

        for p in files:
            print(f"\n--- FILE: {p} ---")
            try:
                lines = []
                ftp.retrlines("RETR " + p, lines.append)
                print("\n".join(lines))
            except Exception as e:
                print(f"Error reading {p}: {e}")

        ftp.quit()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    read_configs()
