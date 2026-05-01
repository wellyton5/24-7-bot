import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def search_json_spawns():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus/custom"

    try:
        ftp.cwd(path)
        items = ftp.nlst()
        print("--- BUSCANDO TRUCK EM ARQUIVOS JSON ---")
        for item in items:
            if item.endswith(".json"):
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {item}", bio.write)
                content = bio.getvalue().decode("utf-8", errors="ignore")
                if "Truck_01_Covered" in content or "Truck_01" in content:
                    print(f"\n[!] Encontrado no arquivo: {item}")
                    # Encontrar a linha e o contexto
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if "Truck_01_Covered" in line or "Truck_01" in line:
                            print(f"  Linha {i + 1}: {line.strip()}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    search_json_spawns()
