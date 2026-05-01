import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def check_custom_events():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    try:
        ftp.cwd("/dayzxb_missions/dayzOffline.chernarusplus/custom/db")
        bio = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        # Encontrar todos os blocos event
        blocks = re.findall(r'<event name="([^"]+)">(.*?)</event>', content, re.DOTALL)

        print("--- EVENTOS EM CUSTOM/DB/EVENTS.XML CONTENDO TRUCK ---")
        for name, body in blocks:
            if "Truck" in body or "truck" in body:
                print(f"\n[!] Evento: {name}")
                print(body)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_custom_events()
