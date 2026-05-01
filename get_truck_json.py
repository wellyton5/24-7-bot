import ftplib
import io
import json
import os
from dotenv import load_dotenv

load_dotenv()


def get_truck_data():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    try:
        bio = io.BytesIO()
        ftp.retrbinary("RETR /profile/truck_availability.json", bio.write)
        content = bio.getvalue().decode("utf-8")
        print(content)
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    get_truck_data()
