import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def find_mapgroupproto_robust():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    print("--- BUSCA ROBUSTA POR MAPGROUPPROTO.XML ---")

    start_dir = "/dayzxb_missions/dayzOffline.chernarusplus"
    try:
        ftp.cwd(start_dir)
        print(f"CWD: {start_dir}")
        items = ftp.nlst()
        if "env" in items:
            ftp.cwd("env")
            print("CWD: env")
            env_items = ftp.nlst()
            for item in env_items:
                if "mapgroupproto.xml" in item.lower():
                    print(f"[!] ENCONTRADO: {ftp.pwd()}/{item}")
                    print(f"Tamanho: {ftp.size(item)}")
        else:
            print("Pasta 'env' não encontrada.")
            # Buscar no root atual
            for item in items:
                if "mapgroupproto.xml" in item.lower():
                    print(f"[!] ENCONTRADO no root: {ftp.pwd()}/{item}")
    except Exception as e:
        print(f"Erro: {e}")

    ftp.quit()


if __name__ == "__main__":
    find_mapgroupproto_robust()
