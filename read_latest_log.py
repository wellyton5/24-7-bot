import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def read_latest():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        candidates = ["/dayzxb/config", "/dayzxb", "/profile"]
        for path in candidates:
            try:
                ftp.cwd(path)
                items = [f for f in ftp.nlst() if f.lower().endswith(".adm")]
                if not items:
                    continue
                items.sort()
                latest = items[-1]
                print(f"Reading {path}/{latest}...")
                lines = []
                ftp.retrlines("RETR " + latest, lines.append)
                for line in lines[-50:]:
                    print(line)
                break
            except Exception as e:
                print(f"Error in {path}: {e}")
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")


if __name__ == "__main__":
    read_latest()
