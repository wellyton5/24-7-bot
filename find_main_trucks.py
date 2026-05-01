import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_main_trucks():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)
        bio = io.BytesIO()
        ftp.retrbinary("RETR types.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print("--- VEÍCULOS (HULLS) ENCONTRADOS EM TYPES.XML ---")

        # Procurar por tipos que não são peças
        types = []
        current_type = []
        in_type = False

        for line in lines:
            if '<type name="' in line:
                in_type = True
                current_type = [line]
            elif in_type:
                current_type.append(line)
                if "</type>" in line:
                    in_type = False
                    block = "\n".join(current_type)
                    type_name_match = re.search(r'type name="([^"]+)"', block)
                    if type_name_match:
                        name = type_name_match.group(1)
                        # Filtrar para caminhões principais e ignorar peças
                        if ("Truck" in name or "M3S" in name) and not any(
                            p in name
                            for p in [
                                "Door",
                                "Wheel",
                                "Hood",
                                "Radiator",
                                "Battery",
                                "FuelCap",
                                "Light",
                                "Engine",
                            ]
                        ):
                            print(f"\n--- {name} ---")
                            print(block)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_main_trucks()
