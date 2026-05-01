import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def apply_heli_fixes():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    # --- 1. AJUSTE EM EVENTS.XML ---
    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"
    print(f"Acessando {path_db}...")
    ftp.cwd(path_db)

    bio_e = io.BytesIO()
    ftp.retrbinary("RETR events.xml", bio_e.write)
    events_xml = bio_e.getvalue().decode("utf-8", errors="ignore")

    # Backup
    with open("events.xml.bak", "w", encoding="utf-8") as f:
        f.write(events_xml)

    print("Modificando events.xml...")
    # Regex para encontrar o bloco StaticHeliCrash e alterar nominal, min, max
    # Buscamos o padrão: <event name="StaticHeliCrash"> ... </event>
    pattern_event = re.compile(
        r'(<event name="StaticHeliCrash">.*?</event>)', re.DOTALL
    )

    def repl_event(match):
        event_content = match.group(1)
        # Alterar nominal para 15
        event_content = re.sub(
            r"<nominal>\d+</nominal>", "<nominal>15</nominal>", event_content
        )
        # Alterar min para 8
        event_content = re.sub(r"<min>\d+</min>", "<min>8</min>", event_content)
        # Alterar max para 12
        event_content = re.sub(r"<max>\d+</max>", "<max>10</max>", event_content)
        return event_content

    new_events_xml = pattern_event.sub(repl_event, events_xml)

    # Upload events.xml
    bio_new_e = io.BytesIO(new_events_xml.encode("utf-8"))
    ftp.storbinary("STOR events.xml", bio_new_e)
    print("events.xml atualizado com sucesso (15 helis).")

    # --- 2. AJUSTE EM MAPGROUPPROTO.XML ---
    path_root = "/dayzxb_missions/dayzOffline.chernarusplus"
    print(f"\nAcessando {path_root}...")
    ftp.cwd(path_root)

    bio_m = io.BytesIO()
    ftp.retrbinary("RETR mapgroupproto.xml", bio_m.write)
    mapgroup_xml = bio_m.getvalue().decode("utf-8", errors="ignore")

    # Backup
    with open("mapgroupproto.xml.bak", "w", encoding="utf-8") as f:
        f.write(mapgroup_xml)

    print("Modificando mapgroupproto.xml...")
    # Remover <category name="tools" /> de Wreck_Mi8, Wreck_Mi8_Crashed, Wreck_UH1Y
    wrecks = ["Wreck_Mi8", "Wreck_Mi8_Crashed", "Wreck_UH1Y"]

    current_xml = mapgroup_xml
    for wreck in wrecks:
        # Padrão: <group name="Wreck_NAME" ...> ... </group>
        # Vamos buscar o bloco e remover a linha de tools
        pattern_wreck = re.compile(f'(<group name="{wreck}".*?</group>)', re.DOTALL)

        def remove_tools(match):
            block = match.group(1)
            # Remove a linha de tools (considerando espaços/tabs)
            new_block = re.sub(
                r'^\s*<category name="tools"\s*/>\s*$', "", block, flags=re.MULTILINE
            )
            return new_block

        current_xml = pattern_wreck.sub(remove_tools, current_xml)

    # Upload mapgroupproto.xml
    bio_new_m = io.BytesIO(current_xml.encode("utf-8"))
    ftp.storbinary("STOR mapgroupproto.xml", bio_new_m)
    print("mapgroupproto.xml atualizado com sucesso (Tools removidas).")

    ftp.quit()
    print("\n--- TODOS OS AJUSTES CONCLUÍDOS ---")


if __name__ == "__main__":
    apply_heli_fixes()
