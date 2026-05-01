import os
import requests
from ftplib import FTP
from dotenv import load_dotenv
import io

load_dotenv()
T = os.getenv("NITRADO_TOKEN")
S = os.getenv("SERVICE_ID")
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def find_gardens():
    # 1. Get latest RPT filename from API
    url = f"https://api.nitrado.net/services/{S}/gameservers/logs"
    headers = {"Authorization": f"Bearer {T}"}
    r = requests.get(url, headers=headers)
    logs = r.json()["data"]["logs"]
    rpt_files = [l for l in logs if l.endswith(".rpt")]
    if not rpt_files:
        print("Nenhum arquivo RPT encontrado.")
        return

    latest_rpt = sorted(rpt_files)[-1]
    print(f"Lendo RPT mais recente: {latest_rpt}")

    # 2. Download and grep via FTP
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)

        # O caminho completo retornado pela API costuma ser relativo à raiz do Nitrado
        # Ex: /dayzxb/config/DayZServer_X1_x64.rpt
        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {latest_rpt}", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.split("\n")
        found = False
        print("--- RESULTADOS DA BUSCA (Garden/Planted) ---")
        for line in lines:
            if any(kw in line.lower() for kw in ["garden", "plot", "planted"]):
                print(line.strip())
                found = True

        if not found:
            print("Nenhum log de garden encontrado no RPT atual.")

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    find_gardens()
