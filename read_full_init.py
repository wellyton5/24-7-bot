import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def read_init():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"
    ftp.cwd(path)

    bio = io.BytesIO()
    ftp.retrbinary("RETR init.c", bio.write)
    content = bio.getvalue().decode("utf-8", errors="ignore")

    print("--- CONTEÚDO DO INIT.C ---")
    print(content)

    ftp.quit()


if __name__ == "__main__":
    read_init()
