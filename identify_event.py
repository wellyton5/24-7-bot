import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def identify_event():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)
        bio = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        target_line = 1223

        # Retroceder para encontrar o nome do evento
        print(f"--- ANALISANDO EVENTO PRÓXIMO À LINHA {target_line} ---")
        for i in range(target_line - 1, -1, -1):
            if '<event name="' in lines[i]:
                print(f"Evento encontrado: {lines[i].strip()}")
                # Mostrar o bloco completo
                for j in range(i, min(i + 40, len(lines))):
                    print(lines[j])
                    if "</event>" in lines[j]:
                        break
                break

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    identify_event()
