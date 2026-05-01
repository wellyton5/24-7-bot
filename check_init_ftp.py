import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_active_init():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    try:
        path = "/dayzxb_missions/dayzOffline.chernarusplus"
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR init.c", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        if "truck_availability" in content:
            print("SCANNER_FOUND")
            # Extrair o bloco de código se possível
            start = content.find("truck_availability")
            print(content[max(0, start - 100) : start + 300])
        else:
            print("SCANNER_NOT_FOUND")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_active_init()
