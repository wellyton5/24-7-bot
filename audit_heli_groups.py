import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def audit_heli_groups():
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

        # Encontrar os grupos das helis
        for name in ["Wreck_Mi8", "Wreck_UH1Y", "Wreck_Mi8_Crashed"]:
            print(f"\n--- AUDITANDO GRUPO: {name} ---")
            pattern = re.compile(f'<group name="{name}".*?>(.*?)</group>', re.DOTALL)
            match = pattern.search(content)
            if match:
                group_body = match.group(1)
                if "Truck" in group_body or "M3S" in group_body:
                    print(f"ALERTA: Truck encontrado no grupo {name}!")
                    print(group_body)
                else:
                    print(f"Grupo {name} parece limpo (nenhum Truck encontrado).")
            else:
                print(f"Grupo {name} não encontrado no mapgroupproto.xml.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    audit_heli_groups()
