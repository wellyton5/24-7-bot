import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def list_xmls():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    paths = [
        "/dayzxb_missions/dayzOffline.chernarusplus",
        "/dayzxb_missions/dayzOffline.chernarusplus/db",
    ]

    print("--- LISTANDO ARQUIVOS XML ---")
    for p in paths:
        try:
            ftp.cwd(p)
            items = ftp.nlst()
            xmls = [f for f in items if f.lower().endswith(".xml")]
            print(f"\nDiretório: {p}")
            for x in xmls:
                print(f"  - {x}")
        except Exception as e:
            print(f"Erro em {p}: {e}")

    ftp.quit()


if __name__ == "__main__":
    list_xmls()
