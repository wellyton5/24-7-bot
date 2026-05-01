import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def list_custom_dir():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    try:
        path = "/dayzxb_missions/dayzOffline.chernarusplus/custom"
        print(f"--- LISTANDO {path} ---")
        ftp.cwd(path)
        items = ftp.nlst()
        for i in items:
            print(f"  {i}")

        print("\n--- TENTANDO ENTRAR EM db ---")
        ftp.cwd("db")
        print("  Sucesso!")
        items_db = ftp.nlst()
        for i in items_db:
            print(f"    {i}")

        print("\n--- TENTANDO LER events.xml ---")
        bio = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio.write)
        print("    Sucesso!")
        content = bio.getvalue().decode("utf-8", errors="ignore")
        print(content[:1000])  # Mostrar começo

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    list_custom_dir()
