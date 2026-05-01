import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def check_wreck_attachments():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgspawnabletypes.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        # Procurar por qualquer tipo que tenha Truck_01_Covered como item de anexo ou cargo
        # Procurar por item name="Truck_01_Covered"
        print("--- BUSCANDO ANEXOS DE Truck_01_Covered EM CFGSPAWNABLETYPES.XML ---")

        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "Truck_01_Covered" in line and '<type name="' not in line:
                print(f"\nMatch na linha {i + 1}: {line.strip()}")
                # Encontrar o pai (o <type name="...">)
                for k in range(i, -1, -1):
                    if '<type name="' in lines[k]:
                        print(f"Pertençe ao tipo: {lines[k].strip()}")
                        # Mostrar o bloco
                        for j in range(k, min(i + 5, len(lines))):
                            print(lines[j])
                        break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_wreck_attachments()
