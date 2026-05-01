import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def find_green_truck():
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
        print("--- BUSCANDO 'Green' OU 'Verd' EM TYPES.XML ---")

        current_type = []
        in_type = False

        for i, line in enumerate(lines):
            if '<type name="' in line:
                in_type = True
                current_type = [line]
            elif in_type:
                current_type.append(line)
                if "</type>" in line:
                    in_type = False
                    block = "\n".join(current_type)
                    if (
                        "green" in block.lower() or "verd" in block.lower()
                    ) and "vehicles" in block.lower():
                        print(f"\nMatch na linha {i + 1}:")
                        print(block)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    find_green_truck()
