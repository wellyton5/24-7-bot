import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_random_presets():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    try:
        ftp.cwd("/dayzxb_missions/dayzOffline.chernarusplus")
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgrandompresets.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        print("--- CFGRANDOMPRESETS.XML ---")
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "Truck" in line or "M3S" in line:
                print(f"Linha {i + 1}: {line.strip()}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_random_presets()
