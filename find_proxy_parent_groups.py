import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_proxy_parent_groups():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR mapgroupproto.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        target_lines = [16530, 16561, 16588, 16619, 17143]

        print("--- IDENTIFICANDO GRUPOS PAI EM MAPGROUPPROTO.XML ---")
        for target in target_lines:
            print(f"\nAnalisando linha {target}...")
            # Retroceder para encontrar o nome do grupo
            for i in range(target - 1, -1, -1):
                if '<group name="' in lines[i]:
                    print(f"Grupo encontrado: {lines[i].strip()}")
                    # Mostrar as primeiras linhas do grupo
                    for j in range(i, min(i + 15, len(lines))):
                        print(f"  {j + 1}: {lines[j]}")
                    break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_proxy_parent_groups()
