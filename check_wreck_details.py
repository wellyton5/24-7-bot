import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def check_wreck_details():
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
        wreck_names = [
            "Land_wreck_truck01_aban1_green_DE",
            "Land_wreck_truck01_aban2_green_DE",
            "StaticObj_Wreck_Ural_DE",
            "Land_Wreck_V3S_DE",
        ]

        print("--- DETALHES DOS WRECKS EM CFGSPAWNABLETYPES.XML ---")
        for wreck in wreck_names:
            print(f"\nBuscando wreck: {wreck}")
            found = False
            for i, line in enumerate(lines):
                if f'type name="{wreck}"' in line:
                    found = True
                    for j in range(i, min(i + 40, len(lines))):
                        print(lines[j])
                        if "</type>" in lines[j]:
                            break
                    break
            if not found:
                print(f"Wreck {wreck} não encontrado.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_wreck_details()
