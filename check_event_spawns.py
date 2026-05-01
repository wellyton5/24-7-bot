import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_event_spawns():
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
        events = ["StaticMilitaryConvoy", "StaticTrain", "StaticHeliCrash"]

        print("--- COMPOSIÇÃO DE EVENTOS EM CFGEVENTSPAWNS.XML ---")
        for event in events:
            print(f"\nBuscando {event}...")
            found = False
            for i, line in enumerate(lines):
                if f'name="{event}"' in line:
                    found = True
                    # Mostrar as primeiras 20 linhas do evento (coordendas costumam vir depois)
                    for j in range(i, min(i + 30, len(lines))):
                        print(lines[j])
                        if "</event>" in lines[j]:
                            break
                    break
            if not found:
                print(f"{event} não encontrado.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_event_spawns()
