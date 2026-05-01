import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def wide_search():
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)
        ftp.cwd("/dayzxb/config")

        all_files = ftp.nlst()
        adm_files = [f for f in all_files if f.endswith(".ADM") and "2026-03-07" in f]

        print(f"Buscando em {len(adm_files)} arquivos ADM...")

        for filename in sorted(adm_files, reverse=True):
            print(f"-- Analisando {filename} --")
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            for line in content.split("\n"):
                # Procurar por Garden ou constructions
                if "garden" in line.lower() or "plot" in line.lower():
                    print(line.strip())

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    wide_search()
