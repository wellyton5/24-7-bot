import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_group_details():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgeventgroups.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        groups = [
            "Supply_Tisy",
            "Abandoned_Kamensk",
            "Train_Mil_Petrovka",
            "Ambush_Grishino",
        ]

        print("--- DETALHES DOS GRUPOS EM CFGEVENTGROUPS.XML ---")
        for group in groups:
            print(f"\nBuscando grupo: {group}")
            found = False
            for i, line in enumerate(lines):
                if f'name="{group}"' in line:
                    found = True
                    for j in range(i, min(i + 30, len(lines))):
                        print(lines[j])
                        if "</group>" in lines[j]:
                            break
                    break
            if not found:
                print(f"Grupo {group} não encontrado.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_group_details()
