import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_land_wreck_truck():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)
        bio = io.BytesIO()
        ftp.retrbinary("RETR types.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print("--- BUSCANDO 'Land_wreck_truck01' EM TYPES.XML ---")

        found = False
        for i, line in enumerate(lines):
            if "Land_wreck_truck01" in line:
                found = True
                print(f"\nMatch na linha {i + 1}:")
                # Mostrar o bloco completo
                start = max(0, i - 1)
                end = min(len(lines), i + 20)
                for j in range(start, end):
                    print(lines[j])
                    if "</type>" in lines[j]:
                        break

        if not found:
            print("'Land_wreck_truck01' NÃO encontrado em types.xml")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_land_wreck_truck()
