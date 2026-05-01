import os
import ftplib
import re
from dotenv import load_dotenv

load_dotenv()

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def fix_truck_types():
    print(f"Conectando a {FTP_HOST}...")
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
    except Exception as e:
        print(f"Erro FTP: {e}")
        return

    path = "/dayzxb_missions/dayzOffline.chernarusplus/db"
    try:
        ftp.cwd(path)
        print(f"Acessando {path}")
    except:
        print(f"Erro ao acessar {path}")
        ftp.quit()
        return

    # Baixar types.xml
    with open("types_to_fix.xml", "wb") as f:
        ftp.retrbinary("RETR types.xml", f.write)

    with open("types_to_fix.xml", "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Regex para o bloco do Truck_01_Covered
    pattern = r'(<type name="Truck_01_Covered">.*?</type>)'

    def replacer(match):
        block = match.group(1)
        # Zerar nominal e min para ele nao ser tratado como loot
        block = re.sub(r"<nominal>\d+</nominal>", "<nominal>0</nominal>", block)
        block = re.sub(r"<min>\d+</min>", "<min>0</min>", block)
        # Remover tags de uso militar e tier (causadores do spawn em helis)
        block = re.sub(r'<usage name="[^"]+"/>', "", block)
        block = re.sub(r'<value name="[^"]+"/>', "", block)
        # Limpar linhas vazias geradas
        block = os.linesep.join([line for line in block.splitlines() if line.strip()])
        return block

    if "Truck_01_Covered" not in content:
        print("Aviso: Truck_01_Covered nao encontrado no types.xml")
    else:
        new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)

        # Backup
        with open("types_to_fix.xml.bak", "w", encoding="utf-8") as f:
            f.write(content)

        with open("types_to_fix.xml", "w", encoding="utf-8") as f:
            f.write(new_content)

        # Upload
        with open("types_to_fix.xml", "rb") as f:
            ftp.storbinary("STOR types.xml", f)
        print("Sucesso: types.xml corrigido! Caminhao verde removido da lista de loot.")

    ftp.quit()


if __name__ == "__main__":
    fix_truck_types()
