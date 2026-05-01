
import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()

def audit_all_events():
    ftp_host = os.getenv('FTP_HOST')
    ftp_user = os.getenv('FTP_USER')
    ftp_pass = os.getenv('FTP_PASS')

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)
        bio = io.BytesIO()
        ftp.retrbinary("RETR events.xml", bio.write)
        content = bio.getvalue().decode('utf-8', errors='ignore')

        # Regex para capturar eventos e seus filhos
        event_pattern = re.compile(r'<event name="([^"]+)">(.*?)</event>', re.DOTALL)
        events = event_pattern.findall(content)

        print(f"--- AUDITORIA DE {len(events)} EVENTOS EM EVENTS.XML ---")
        for name, body in events:
            child_pattern = re.compile(r'type="([^"]+)"')
            children = child_pattern.findall(body)
            if children:
                if any("Truck" in c for c in children):
                    print(f"\n[TRUCK FOUND] Evento: {name}")
                    for c in children:
                        print(f"  - Child: {c}")
                elif any(k in name for k in ["Heli", "Convoy", "Train"]):
                    print(f"\nEvento Mil/Event: {name}")
                    for c in children:
                        print(f"  - Child: {c}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()

if __name__ == "__main__":
    audit_all_events():
