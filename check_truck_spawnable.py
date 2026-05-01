import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_truck_spawnable():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgspawnabletypes.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print("--- CONFIGURAÇÃO DE TRUCK EM CFGSPAWNABLETYPES.XML ---")

        found = False
        for i, line in enumerate(lines):
            if '<type name="Truck_01_Covered"' in line:
                found = True
                print(f"\nLinha {i + 1}:")
                for j in range(i, min(i + 150, len(lines))):
                    print(lines[j])
                    if "</type>" in lines[j]:
                        break

        if not found:
            print("Truck_01_Covered não encontrado em cfgspawnabletypes.xml")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_truck_spawnable()
