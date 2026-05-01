import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def find_today(ftp, path="/", depth=0):
    if depth > 3:
        return
    try:
        items = ftp.nlst(path)
        for i in items:
            full = i if i.startswith("/") else path.rstrip("/") + "/" + i
            if "2026-02-15" in i:
                print(f"FOUND: {full}")
            if "." not in i:
                find_today(ftp, full, depth + 1)
    except:
        pass


if __name__ == "__main__":
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        find_today(ftp)
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")
