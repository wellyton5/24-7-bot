import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def list_all(ftp, path, depth=0):
    if depth > 3:
        return
    try:
        print(f"Listing {path}...")
        items = ftp.nlst(path)
        for item in items:
            print(f"- {item}")
            # If it doesn't have a dot, assume it's a folder and recurse
            name = item.split("/")[-1]
            if "." not in name:
                list_all(
                    ftp, item if item.startswith("/") else f"{path}/{item}", depth + 1
                )
    except Exception as e:
        print(f"Error {path}: {e}")


if __name__ == "__main__":
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        list_all(ftp, "/dayzxb")
        ftp.quit()
    except Exception as e:
        print(f"Error: {e}")
