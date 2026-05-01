import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def verify_mapgroupproto_path():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    print("--- VERIFICANDO CAMINHOS PARA MAPGROUPPROTO.XML ---")
    paths_to_check = [
        "/dayzxb_missions/dayzOffline.chernarusplus/env/mapgroupproto.xml",
        "/dayzxb_missions/dayzOffline.chernarusplus/mapgroupproto.xml",
        "env/mapgroupproto.xml",
        "mapgroupproto.xml",
    ]

    for p in paths_to_check:
        try:
            size = ftp.size(p)
            print(f"[!] ENCONTRADO: {p} (Tamanho: {size})")
        except:
            print(f"[ ] Não encontrado: {p}")

    ftp.quit()


if __name__ == "__main__":
    verify_mapgroupproto_path()
