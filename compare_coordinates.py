import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def compare_coordinates():
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

        # Extrair blocos de eventos
        event_blocks = re.findall(
            r'<event name="([^"]+)">(.*?)</event>', content, re.DOTALL
        )

        coords = {}
        for name, block in event_blocks:
            # Extrair todas as coordenadas (x e z)
            pos_matches = re.findall(r'x="([^"]+)"\s+z="([^"]+)"', block)
            coords[name] = [(float(x), float(z)) for x, z in pos_matches]

        print("--- COMPARANDO COORDENADAS ---")

        truck_coords = coords.get("VehicleTruck01", [])
        events_to_check = ["StaticMilitaryConvoy", "StaticHeliCrash", "StaticTrain"]

        for event_name in events_to_check:
            e_coords = coords.get(event_name, [])
            print(f"\nComparando VehicleTruck01 com {event_name}:")
            matches = 0
            for tx, tz in truck_coords:
                for ex, ez in e_coords:
                    # Margem de erro de 5 metros para considerar "mesmo lugar"
                    if abs(tx - ex) < 5 and abs(tz - ez) < 5:
                        print(
                            f"  [CONFLITO] Coordenada similar encontrada: ({tx}, {tz})"
                        )
                        matches += 1
            if matches == 0:
                print("  Nenhum conflito direto de coordenadas encontrado.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    compare_coordinates()
