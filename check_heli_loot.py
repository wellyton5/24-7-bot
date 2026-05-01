import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_heli_event():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus/db"
    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        # Procurar pelo evento de helicóptero
        lines = content.splitlines()
        found_heli = False
        print("--- CONFIGURAÇÃO DO EVENTO HELICÓPTERO ---")
        for i, line in enumerate(lines):
            if 'name="StaticHelicopter"' in line or 'name="EventHelicopter"' in line:
                found_heli = True
                # Mostrar as próximas 20 linhas do evento
                for j in range(i, min(i + 30, len(lines))):
                    print(lines[j])
                break

        if not found_heli:
            print("Evento de helicóptero não encontrado em events.xml")

    except Exception as e:
        print(f"Erro ao acessar {path}/events.xml: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_heli_event()
