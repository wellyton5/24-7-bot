import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_m3s():
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

        # Procurar por qualquer bloco que tenha o nome M3S
        pattern = re.compile(r'<type name="M3S_Covered">.*?</type>', re.DOTALL)
        matches = pattern.findall(content)

        print("--- BLOCOS M3S_Covered ENCONTRADOS ---")
        for m in matches:
            print(m)

        # Procurar por M3S_Chassis
        pattern2 = re.compile(r'<type name="M3S_Chassis">.*?</type>', re.DOTALL)
        matches2 = pattern2.findall(content)
        print("\n--- BLOCOS M3S_Chassis ENCONTRADOS ---")
        for m in matches2:
            print(m)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_m3s()
