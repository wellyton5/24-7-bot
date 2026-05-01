import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def verify_fixes():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    # --- 1. VERIFICAÇÃO EM EVENTS.XML ---
    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"
    print(f"Verificando {path_db}/events.xml...")
    ftp.cwd(path_db)

    bio_e = io.BytesIO()
    ftp.retrbinary("RETR events.xml", bio_e.write)
    events_xml = bio_e.getvalue().decode("utf-8", errors="ignore")

    pattern_event = re.compile(
        r'(<event name="StaticHeliCrash">.*?</event>)', re.DOTALL
    )
    match = pattern_event.search(events_xml)
    if match:
        print("\n[events.xml] Configuração atual do StaticHeliCrash:")
        print(match.group(1))
    else:
        print("\n[ERROR] Bloco StaticHeliCrash não encontrado em events.xml")

    # --- 2. VERIFICAÇÃO EM MAPGROUPPROTO.XML ---
    path_root = "/dayzxb_missions/dayzOffline.chernarusplus"
    print(f"\nVerificando {path_root}/mapgroupproto.xml...")
    ftp.cwd(path_root)

    bio_m = io.BytesIO()
    ftp.retrbinary("RETR mapgroupproto.xml", bio_m.write)
    mapgroup_xml = bio_m.getvalue().decode("utf-8", errors="ignore")

    wrecks = ["Wreck_Mi8", "Wreck_Mi8_Crashed", "Wreck_UH1Y"]
    for wreck in wrecks:
        pattern_wreck = re.compile(f'(<group name="{wreck}".*?</group>)', re.DOTALL)
        match_w = pattern_wreck.search(mapgroup_xml)
        if match_w:
            block = match_w.group(1)
            print(f"\n[{wreck}] Contém 'tools'?")
            if 'category name="tools"' in block:
                print(">>> AINDA CONTÉM (ERRO)")
                # Print just the categories to see
                for line in block.splitlines():
                    if "category" in line:
                        print(line)
            else:
                print(">>> NÃO CONTÉM (SUCESSO)")
        else:
            print(f"\n[ERROR] Bloco {wreck} não encontrado.")

    ftp.quit()


if __name__ == "__main__":
    verify_fixes()
