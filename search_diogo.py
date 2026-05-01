import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def search_diogo():
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)
        ftp.cwd("/dayzxb/config")

        # Analisar o ADM mais recente
        filename = "DayZServer_X1_x64_2026-03-07_19-57-12.ADM"
        print(f"-- Analisando {filename} --")
        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.split("\n")
        for line in lines:
            if "diogo selva" in line.lower():
                print(line.strip())

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    search_diogo()
