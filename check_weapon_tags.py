import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_weapon_tags():
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
        weapons = ["M4A1", "SVD", "SVAL", "VSS", "FAL", "DMR"]

        print("--- TAGS DE ARMAS MILITARES ---")
        for w in weapons:
            found = False
            for i, line in enumerate(lines):
                if f'type name="{w}"' in line:
                    found = True
                    print(f"\nArma: {w}")
                    for j in range(i, min(i + 25, len(lines))):
                        print(lines[j])
                        if "</type>" in lines[j]:
                            break
                    break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_weapon_tags()
