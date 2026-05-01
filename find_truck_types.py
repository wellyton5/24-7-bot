import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def find_truck_types():
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
        print("--- CAMINHÕES ENCONTRADOS EM TYPES.XML ---")
        for i, line in enumerate(lines):
            if '<type name="Truck' in line or '<type name="M3S' in line:
                print(f"\nLinha {i + 1}:")
                for j in range(i, min(i + 25, len(lines))):
                    print(lines[j])
                    if "</type>" in lines[j]:
                        break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_truck_types()
