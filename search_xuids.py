import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def search_xuids(xuids):
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)
        ftp.cwd("/dayzxb/config")

        all_files = ftp.nlst()
        adm_files = sorted([f for f in all_files if f.endswith(".ADM")])[-3:]

        for filename in adm_files:
            print(f"-- Analisando {filename} --")
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            for line in content.split("\n"):
                if any(x in line for x in xuids):
                    print(line.strip())

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    search_xuids(
        [
            "6D7C287C12990A3744FC0B498A589D649CE3A31C",
            "F419EFD3D49049927D2968128C4A300A209CE74B",
        ]
    )
