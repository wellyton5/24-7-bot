import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_convoys_trains():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_root = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        # 1. Search in cfgspawnabletypes.xml
        ftp.cwd(path_root)
        bio_s = io.BytesIO()
        ftp.retrbinary("RETR cfgspawnabletypes.xml", bio_s.write)
        spawnable_content = bio_s.getvalue().decode("utf-8", errors="ignore")

        print("--- BUSCANDO CONVOY/TRAIN EM CFGSPAWNABLETYPES.XML ---")
        lines_s = spawnable_content.splitlines()
        for i, line in enumerate(lines_s):
            if any(k in line for k in ["Convoy", "Train", "Static"]):
                if '<type name="' in line:
                    print(f"\nTipo encontrado: {line.strip()} (Linha {i + 1})")
                    for j in range(i, min(i + 40, len(lines_s))):
                        print(lines_s[j])
                        if "</type>" in lines_s[j]:
                            break

        # 2. Search in events.xml
        ftp.cwd("db")
        bio_e = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio_e.write)
        events_content = bio_e.getvalue().decode("utf-8", errors="ignore")

        print("\n--- BUSCANDO CONVOY/TRAIN EM EVENTS.XML ---")
        lines_e = events_content.splitlines()
        for i, line in enumerate(lines_e):
            if '<event name="' in line and any(k in line for k in ["Convoy", "Train"]):
                print(f"\nEvento encontrado: {line.strip()} (Linha {i + 1})")
                for j in range(i, min(i + 40, len(lines_e))):
                    print(lines_e[j])
                    if "</event>" in lines_e[j]:
                        break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_convoys_trains()
