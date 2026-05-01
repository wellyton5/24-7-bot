import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_shortstick_exact():
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
        print("--- BUSCA EXATA POR 'ShortStick' EM TYPES.XML ---")
        found = False
        for i, line in enumerate(lines):
            if 'name="ShortStick"' in line:
                found = True
                print(f"Encontrado na linha {i + 1}:")
                for j in range(i, min(i + 20, len(lines))):
                    print(lines[j])
                    if "</type>" in lines[j]:
                        break

        if not found:
            print("ShortStick NÃO encontrado.")

        print("\n--- BUSCA POR NOMINAIS DE ARMAS MILITARES ---")
        weapons = ["M4A1", "SVD", "VSS", "KA101", "DMR", "AUG"]
        for w in weapons:
            for i, line in enumerate(lines):
                if f'type name="{w}"' in line:
                    print(f"[{w}] Linha {i + 1}: {lines[i + 1].strip()} (Nominal)")
                    break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_shortstick_exact()
