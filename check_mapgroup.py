import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_mapgroup():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR mapgroupproto.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        wrecks = ["Mi8", "UH1Y", "Heli"]

        print("--- DEFINIÇÕES DE PONTOS DE LOOT EM MAPGROUPPROTO.XML ---")
        for wreck in wrecks:
            print(f"\nBuscando {wreck}...")
            found_count = 0
            for i, line in enumerate(lines):
                if wreck in line and "<group" in line:
                    for j in range(i, min(i + 20, len(lines))):
                        print(lines[j])
                        if "</group>" in lines[j]:
                            break
                    found_count += 1
                    if found_count > 3:
                        break  # Limite de amostragem

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_mapgroup()
