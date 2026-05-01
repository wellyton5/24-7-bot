import os
import ftplib
import re
from dotenv import load_dotenv

# Carregar variáveis do .env da VPS
load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def optimize_events():
    print(f"Conectando a {FTP_HOST}...")
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
    except Exception as e:
        print(f"Erro na conexao FTP: {e}")
        return

    # Caminho corrigido baseado na estrutura do Nitrado observada no init.c
    paths = ["/dayzxb_missions/dayzOffline.chernarusplus/db", "/dayzxb/db", "/db"]
    events_path = None

    for p in paths:
        try:
            ftp.cwd(p)
            files = ftp.nlst()
            if "events.xml" in files:
                events_path = p
                print(f"Arquivo encontrado em {p}")
                break
        except:
            continue

    if not events_path:
        print("Erro: events.xml nao encontrado nos caminhos conhecidos.")
        ftp.quit()
        return

    # Baixar para edicao
    with open("events_temp.xml", "wb") as f:
        ftp.retrbinary("RETR events.xml", f.write)

    with open("events_temp.xml", "r", encoding="utf-8") as f:
        content = f.read()

    # Regex para VehicleTruck01
    event_pattern = r'(<event name="VehicleTruck01">.*?</event>)'

    def replacer(match):
        block = match.group(1)
        # Substituir nominal, min, max para 10
        block = re.sub(r"<nominal>\d+</nominal>", "<nominal>10</nominal>", block)
        block = re.sub(r"<min>\d+</min>", "<min>10</min>", block)
        block = re.sub(r"<max>\d+</max>", "<max>10</max>", block)
        # Substituir lifetime para 4 horas (14400s)
        block = re.sub(r"<lifetime>\d+</lifetime>", "<lifetime>14400</lifetime>", block)
        # Ativar deletable="1" para seguranca
        block = re.sub(r'deletable="\d+"', 'deletable="1"', block)

        # Filtrar children: Deixar apenas Truck_01_Covered (Verde Militar)
        children_start = block.find("<children>")
        children_end = block.find("</children>") + len("</children>")

        new_children = """<children>
            <child lootmax="0" lootmin="0" max="10" min="8" type="Truck_01_Covered" />
        </children>"""

        block = block[:children_start] + new_children + block[children_end:]
        return block

    if "VehicleTruck01" not in content:
        print("Aviso: Evento VehicleTruck01 nao encontrado.")
    else:
        new_content = re.sub(event_pattern, replacer, content, flags=re.DOTALL)

        # Salvar backup local na VPS antes do envio
        with open("events_temp.xml.bak", "w", encoding="utf-8") as f:
            f.write(content)

        with open("events_temp.xml", "w", encoding="utf-8") as f:
            f.write(new_content)

        # Upload definitivo
        with open("events_temp.xml", "rb") as f:
            ftp.storbinary("STOR events.xml", f)
        print("Sucesso: events.xml otimizado para 10 Trucks (Covered) e enviado!")

    ftp.quit()


if __name__ == "__main__":
    optimize_events()
