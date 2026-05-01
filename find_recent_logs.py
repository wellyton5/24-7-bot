import ftplib, os, time
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def find_recent(ftp, path="/", depth=0):
    if depth > 3:
        return
    try:
        items = ftp.nlst(path)
        for i in items:
            full = i if i.startswith("/") else path.rstrip("/") + "/" + i
            if "." in i:
                try:
                    # MDTM is not always supported, but let's try
                    mtime_str = ftp.sendcmd(f"MDTM {full}").split()[1]
                    # Format: YYYYMMDDHHMMSS
                    # print(f"FILE: {full} | MTIME: {mtime_str}")
                    # If modified in the last 15 minutes (approx)
                    # For now just print all with ADM extension
                    if full.lower().endswith(".adm"):
                        print(f"ADM: {full} | MTIME: {mtime_str}")
                except:
                    pass
            else:
                find_recent(ftp, full, depth + 1)
    except:
        pass


if __name__ == "__main__":
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        find_recent(ftp)
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")
