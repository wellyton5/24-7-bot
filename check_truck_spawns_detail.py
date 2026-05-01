import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_truck_spawns_detail():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgeventspawns.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print("--- COORDENADAS DE VehicleTruck01 EM CFGEVENTSPAWNS.XML ---")

        found = False
        for i, line in enumerate(lines):
            if 'name="VehicleTruck01"' in line:
                found = True
                for j in range(i, min(i + 150, len(lines))):
                    print(lines[j])
                    if "</event>" in lines[j]:
                        break
                break

        if not found:
            print("VehicleTruck01 não encontrado em cfgeventspawns.xml")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_truck_spawns_detail()
