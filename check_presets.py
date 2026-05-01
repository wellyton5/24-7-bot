import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_presets_and_shortstick():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"
    path_root = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        # 1. Checar ShortStick no types.xml
        ftp.cwd(path_db)
        bio_t = io.BytesIO()
        ftp.retrbinary("RETR types.xml", bio_t.write)
        content_t = bio_t.getvalue().decode("utf-8", errors="ignore")

        lines_t = content_t.splitlines()
        print("--- CONFIGURAÇÃO DE SHORTSTICK EM TYPES.XML ---")
        for i, line in enumerate(lines_t):
            if 'name="ShortStick"' in line:
                for j in range(i, min(i + 20, len(lines_t))):
                    print(lines_t[j])
                    if "</type>" in lines_t[j]:
                        break

        # 2. Checar cfgrandompresets.xml
        ftp.cwd(path_root)
        bio_r = io.BytesIO()
        ftp.retrbinary("RETR cfgrandompresets.xml", bio_r.write)
        content_r = bio_r.getvalue().decode("utf-8", errors="ignore")

        print("\n--- BUSCANDO PRESETS COM 'STICK' ---")
        lines_r = content_r.splitlines()
        for i, line in enumerate(lines_r):
            if "Stick" in line:
                # Mostrar o bloco do preset
                start = max(0, i - 10)
                end = min(len(lines_r), i + 10)
                print(f"\nMatch na linha {i + 1}:")
                for j in range(start, end):
                    print(lines_r[j])

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_presets_and_shortstick()
