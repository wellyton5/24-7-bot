import io
import os
import re
import sqlite3
import math
from dotenv import load_dotenv
from ftp_helpers import connect_ftp
import database

load_dotenv()


# Mesmo parser corrigido do main_24-7.py
def get_base_at_local(x, z):
    bases = database.get_security_bases()
    for base in bases:
        dist = math.sqrt((x - base["x"]) ** 2 + (z - base["z"]) ** 2)
        if dist <= base["radius"]:
            return base
    return None


def process_line_backfill(line):
    line = line.strip()
    if not line:
        return

    pattern = r'Player "(?P<name>[^"]+)" \(id=[^ ]+ pos=<(?P<coords>[^>]+)>\)(?P<action_line>.+)'
    match = re.search(pattern, line)
    if not match:
        pattern_alt = r'Player "(?P<name>[^"]+)" .*(?:at|pos)=<(?P<coords>[^>]+)>.*'
        match = re.search(pattern_alt, line)
        if not match:
            return

    player_name = match.group("name")
    coords_str = match.group("coords")
    action_line = (
        match.group("action_line") if "action_line" in match.groupdict() else line
    )

    try:
        x, y, z = map(float, coords_str.split(","))
    except:
        return

    action_line_lower = action_line.lower()

    if "built" in action_line_lower or "placed" in action_line_lower:
        if "fence" in action_line_lower or "gate" in action_line_lower:
            base = get_base_at_local(x, z)
            if not base:
                database.register_new_base(player_name, x, z)
                print(f"[RECOVERY] Base registrada para {player_name} em {x}, {z}")


def backfill_bases():
    ftp = connect_ftp()
    if not ftp:
        return

    print("Iniciando recuperação de bases perdidas...")
    database.init_db()

    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            # Pegar logs de hoje (14 e 15/02 UTC)
            adm_files = [
                f"{path}/{f}"
                for f in items
                if f.lower().endswith(".adm")
                and ("2026-02-14" in f or "2026-02-15" in f)
            ]

            for log_file in sorted(adm_files):
                print(f"Processando log: {log_file}")
                ftp.voidcmd("TYPE I")
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {log_file}", bio.write)
                content = bio.getvalue().decode("utf-8", errors="ignore")

                for line in content.split("\n"):
                    process_line_backfill(line)
        except Exception as e:
            print(f"Erro no diretório {path}: {e}")
            continue


if __name__ == "__main__":
    backfill_bases()
    print("Recuperação concluída.")
