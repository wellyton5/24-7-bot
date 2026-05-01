import os
import ftplib
import re
from dotenv import load_dotenv

load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def check_xml_bugs():
    print(f"Conectando a {FTP_HOST}...")
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
    except Exception as e:
        print(f"Erro FTP: {e}")
        return

    # Pastas de missao e db
    paths = [
        "/dayzxb_missions/dayzOffline.chernarusplus/db",
        "/dayzxb_missions/dayzOffline.chernarusplus",
    ]
    files_to_check = ["events.xml", "cfgspawnabletypes.xml"]

    found_files = {}
    for p in paths:
        try:
            ftp.cwd(p)
            nlst = ftp.nlst()
            for f in files_to_check:
                if f in nlst:
                    local_name = f"check_{f}"
                    with open(local_name, "wb") as lf:
                        ftp.retrbinary(f"RETR {f}", lf.write)
                    found_files[f] = local_name
        except:
            continue

    # Analise 1: Duplicidade no events.xml
    if "events.xml" in found_files:
        with open(
            found_files["events.xml"], "r", encoding="utf-8", errors="ignore"
        ) as f:
            content = f.read()
            # Encontrar todos os blocos <event> que contenham Truck_01_Covered
            # Usando uma regex para pegar o nome do evento e o conteúdo
            events = re.findall(
                r'<event name="([^"]+)">.*?(Truck_01_Covered).*?</event>',
                content,
                re.DOTALL,
            )
            print("\n=== Analise events.xml ===")
            if len(events) > 1:
                print(
                    f"ATENCAO: O modelo Truck_01_Covered aparece em {len(events)} eventos diferentes!"
                )
                for ev_name, _ in events:
                    print(f" - Evento: {ev_name}")
            else:
                print("Truck_01_Covered aparece apenas em 1 evento (VehicleTruck01).")

    # Analise 2: cfgspawnabletypes.xml (Onde o Kit foi colocado)
    if "cfgspawnabletypes.xml" in found_files:
        with open(
            found_files["cfgspawnabletypes.xml"], "r", encoding="utf-8", errors="ignore"
        ) as f:
            content = f.read()
            # Procurar o bloco do Truck_01_Covered
            pattern = r'<type name="Truck_01_Covered">.*?</type>'
            match = re.search(pattern, content, re.DOTALL)
            print("\n=== Analise cfgspawnabletypes.xml ===")
            if match:
                block = match.group(0)
                print(f"Configuracao encontrada:\n{block}")
                # Verificar se ha 'attachments' ou 'cargo' que possam causar conflito
                # Ou se ele foi colocado dentro de outro type por engano
            else:
                print("Truck_01_Covered nao encontrado no cfgspawnabletypes.xml")

    ftp.quit()


if __name__ == "__main__":
    check_xml_bugs()
