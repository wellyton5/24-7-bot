import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_stick_and_event():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)

        # 1. Checar o evento completo
        bio_e = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio_e.write)
        events_xml = bio_e.getvalue().decode("utf-8", errors="ignore")

        lines_e = events_xml.splitlines()
        print("--- EVENTO STATIC HELI CRASH COMPLETO ---")
        for i, line in enumerate(lines_e):
            if 'name="StaticHeliCrash"' in line:
                for j in range(i, min(i + 40, len(lines_e))):
                    print(lines_e[j])
                    if "</event>" in lines_e[j]:
                        break
                break

        # 2. Checar a WoodenStick
        bio_t = io.BytesIO()
        ftp.retrbinary("RETR types.xml", bio_t.write)
        types_xml = bio_t.getvalue().decode("utf-8", errors="ignore")

        lines_t = types_xml.splitlines()
        print("\n--- CONFIGURAÇÃO DA WOODENSTICK ---")
        found_stick = False
        for i, line in enumerate(lines_t):
            if 'name="WoodenStick"' in line or 'name="ShortStick"' in line:
                found_stick = True
                for j in range(i, min(i + 20, len(lines_t))):
                    print(lines_t[j])
                    if "</type>" in lines_t[j]:
                        break
                # Continue buscando outras ocorrências se necessário

        if not found_stick:
            print("WoodenStick ou ShortStick não encontrados em types.xml")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_stick_and_event()
