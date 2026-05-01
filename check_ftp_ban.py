import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def check_ban_txt():
    try:
        print(f"Conectando a {FTP_HOST}...")
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        ban_path = "/dayzxb/config/ban.txt"
        print(f"Lendo {ban_path}...")

        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {ban_path}", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        print("\n--- CONTEÚDO DO BAN.TXT ---")
        print(content)
        print("--- FIM ---")

        ftp.quit()
    except Exception as e:
        print(f"Erro ao acessar FTP: {e}")


if __name__ == "__main__":
    check_ban_txt()
