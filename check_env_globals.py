import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_env_globals():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    try:
        # 1. cfgenvironment.xml
        ftp.cwd("/dayzxb_missions/dayzOffline.chernarusplus")
        bio_e = io.BytesIO()
        ftp.retrbinary("RETR cfgenvironment.xml", bio_e.write)
        print("--- CFGENVIRONMENT.XML ---")
        print(bio_e.getvalue().decode("utf-8", errors="ignore"))

        # 2. globals.xml
        ftp.cwd("db")
        bio_g = io.BytesIO()
        ftp.retrbinary("RETR globals.xml", bio_g.write)
        print("\n--- GLOBALS.XML ---")
        print(bio_g.getvalue().decode("utf-8", errors="ignore"))

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_env_globals()
