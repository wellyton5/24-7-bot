import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def check_group_proxies_deep():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR mapgroupproto.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        # Encontrar os blocos das wrecks de caminhão
        wreck_names = [
            "Land_wreck_truck01_aban1_green_DE",
            "Land_wreck_truck01_aban2_green_DE",
            "Land_wreck_truck01_aban1_orange_DE",
            "Land_wreck_truck01_aban1_blue_DE",
        ]

        print("--- AUDITANDO PROXIES DE WRECKS DE CAMINHÃO EM MAPGROUPPROTO.XML ---")
        for name in wreck_names:
            print(f"\n--- GRUPO: {name} ---")
            pattern = re.compile(f'<group name="{name}".*?>(.*?)</group>', re.DOTALL)
            match = pattern.search(content)
            if match:
                group_body = match.group(1)
                # Listar todos os proxies
                proxies = re.findall(r'<proxy type="([^"]+)"', group_body)
                for p in proxies:
                    print(f"  - Proxy: {p}")
                    if p == "Truck_01_Covered" or p == "Truck_01":
                        print(
                            "    [!] AQUI ESTÁ O ERRO! Proxy de caminhão vivo em wreck estática!"
                        )
            else:
                print(f"Grupo {name} não encontrado.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_group_proxies_deep()
