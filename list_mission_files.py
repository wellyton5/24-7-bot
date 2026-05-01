import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def list_files():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        path = "/dayzxb_missions/dayzOffline.chernarusplus"
        print(f"Listing {path}:")
        print(ftp.nlst(path))

        # Check if custom folder exists and list it
        custom_path = path + "/custom"
        print(f"Listing {custom_path}:")
        try:
            print(ftp.nlst(custom_path))
        except:
            print("Custom folder not found.")

        # Check if db folder exists and list it
        db_path = path + "/db"
        print(f"Listing {db_path}:")
        try:
            print(ftp.nlst(db_path))
        except:
            print("DB folder not found.")

        ftp.quit()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_files()
