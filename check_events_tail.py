import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_events_tail():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)
        bio = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print(f"--- FIM DO ARQUIVO EVENTS.XML (Total {len(lines)} linhas) ---")
        for j in range(len(lines) - 50, len(lines)):
            print(f"{j + 1}: {lines[j]}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_events_tail()
