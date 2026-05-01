import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_truck_in_groups():
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
        print("--- BUSCANDO 'Truck_01_Covered' EM CFGEVENTGROUPS.XML ---")

        found = False
        for i, line in enumerate(lines):
            if "Truck_01_Covered" in line:
                found = True
                print(f"\nMatch na linha {i + 1}:")
                # Mostrar o bloco completo (group)
                # Retroceder até o início do grupo
                for k in range(i, -1, -1):
                    if '<group name="' in lines[k]:
                        print(f"No grupo: {lines[k].strip()}")
                        for j in range(k, min(i + 10, len(lines))):
                            print(lines[j])
                        break

        if not found:
            print("'Truck_01_Covered' NÃO encontrado em cfgeventgroups.xml")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_truck_in_groups()
