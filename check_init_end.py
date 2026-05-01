import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_init_end():
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

    print("--- FIM DO INIT.C (ÚLTIMAS 20 LINHAS) ---")
    lines = content.splitlines()
    for line in lines[-20:]:
        print(line)

    ftp.quit()


if __name__ == "__main__":
    check_init_end()
