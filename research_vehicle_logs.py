import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_vehicle_logs():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb/config"
    ftp.cwd(path)

    items = ftp.nlst()
    # Pega os 2 ADMs mais recentes
    adms = [i for i in items if i.endswith(".ADM")]
    adms.sort(reverse=True)

    for adm_name in adms[:2]:
        print(f"\n--- PESQUISANDO EM: {adm_name} ---")
        try:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {adm_name}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            lines = content.splitlines()
            # Procurar por padrões de entrada em veículos
            # Ex: "into", "from", "vehicle"
            patterns = [r"into", r"from", r"vehicle", r"Truck", r"Sedan", r"Hatchback"]

            for line in lines:
                if any(re.search(p, line, re.IGNORECASE) for p in patterns):
                    # Filtrar apenas linhas que pareçam ser de interação (ter coordenadas ou nomes)
                    if '"' in line and ("pos=<" in line or "(" in line):
                        print(line)
        except Exception as e:
            print(f"Erro ao ler {adm_name}: {e}")

    ftp.quit()


if __name__ == "__main__":
    find_vehicle_logs()
