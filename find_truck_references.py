import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_truck_references():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        files = ["cfgspawnabletypes.xml", "db/events.xml"]

        for f_path in files:
            print(f"\n--- BUSCANDO EM {f_path} ---")
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {f_path}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "Truck_01_Covered" in line or "Truck_01" in line:
                    # Verificar se não é a própria definição
                    # Na definição seria <type name="Truck_01_Covered">
                    # No uso seria <item name="Truck_01_Covered"> ou <child type="Truck_01_Covered">
                    if (
                        'item name="' in line
                        or 'type="' in line
                        or 'child type="' in line
                    ):
                        print(f"Match na linha {i + 1}: {line.strip()}")
                        # Mostrar contexto para ver o pai
                        start = max(0, i - 10)
                        end = min(len(lines), i + 2)
                        for j in range(start, end):
                            print(f"  {j + 1}: {lines[j]}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_truck_references()
