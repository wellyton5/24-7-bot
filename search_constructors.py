import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def search_constructors():
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)
        ftp.cwd("/dayzxb/config")

        all_files = ftp.nlst()
        adm_files = [f for f in all_files if f.endswith(".ADM") and "2026-03-07" in f]

        print(f"Buscando ações de 'Construtor' em {len(adm_files)} arquivos...")

        for filename in sorted(adm_files, reverse=True):
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            lines = content.split("\n")
            for line in lines:
                if "Construtor" in line:
                    # Se tiver built ou placed, mostrar
                    if any(
                        kw in line.lower()
                        for kw in ["built", "placed", "destroyed", "dismantled"]
                    ):
                        print(f"[{filename}] {line.strip()}")

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    search_constructors()
