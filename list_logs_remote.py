import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def list_logs():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
            try:
                print(f"Listing {path}:")
                ftp.cwd(path)
                items = [f for f in ftp.nlst() if f.lower().endswith(".adm")]
                items.sort()
                for i in items[-10:]:
                    print(f"  {i}")
            except:
                pass
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")


if __name__ == "__main__":
    list_logs()
