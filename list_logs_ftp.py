import os
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def list_logs():
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)

        # Caminho padrão de logs no Nitrado Xbox
        path = "/dayzxb/config"
        print(f"Listando arquivos em {path}...")
        ftp.cwd(path)

        files = []
        ftp.dir(files.append)

        for f in files:
            if ".rpt" in f.lower() or ".adm" in f.lower():
                print(f)

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    list_logs()
