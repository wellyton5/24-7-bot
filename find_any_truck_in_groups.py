import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_any_truck_in_groups():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgeventgroups.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print("--- BUSCANDO QUALQUER 'TRUCK' EM CFGEVENTGROUPS.XML ---")

        for i, line in enumerate(lines):
            if "Truck" in line or "truck" in line:
                print(f"\nMatch na linha {i + 1}: {line.strip()}")
                # Encontrar o grupo pai
                for k in range(i, -1, -1):
                    if '<group name="' in lines[k]:
                        print(f"No grupo: {lines[k].strip()}")
                        break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_any_truck_in_groups()
