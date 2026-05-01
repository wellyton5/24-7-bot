import sqlite3
import os
import re
import math
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def get_bases():
    conn = sqlite3.connect("security.db")
    cur = conn.cursor()
    cur.execute("SELECT owner, x, z, owner_discord_id FROM bases")
    bases = [
        {"owner": r[0], "x": r[1], "z": r[2], "discord": r[3]} for r in cur.fetchall()
    ]
    conn.close()
    return bases


def audit_bases_activity():
    bases = get_bases()
    print(f"Monitorando {len(bases)} bases registradas.")

    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)
        ftp.cwd("/dayzxb/config")

        all_files = ftp.nlst()
        # Analisar os 2 ADMs mais recentes
        adm_files = sorted([f for f in all_files if f.endswith(".ADM")])[-2:]

        for filename in adm_files:
            print(f"\n--- AUDITANDO {filename} ---")
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            lines = content.split("\n")
            for line in lines:
                # Ex: 20:40:46 | Player "leon9 sk8" (id=...) pos=<2214.5, 11095.1, 265.2>)Built/Placed ...
                if "Built" in line or "placed" in line:
                    match = re.search(
                        r'Player "(.*?)" .*?pos=<(.*?), (.*?), (.*?)>\)(Built|placed) (.*)',
                        line,
                    )
                    if match:
                        player = match.group(1)
                        px, py, pz = (
                            float(match.group(2)),
                            float(match.group(3)),
                            float(match.group(4)),
                        )
                        action = match.group(5)
                        item = match.group(6)

                        # Verificar proximidade com alguma base
                        for base in bases:
                            dist = math.hypot(px - base["x"], pz - base["z"])
                            if dist < 100:
                                if player != base["owner"]:
                                    # Verificar se é clan? (simplificado aqui por GT)
                                    print(
                                        f"SUSPEITO: {player} {action} {item} a {dist:.1f}m da base de {base['owner']} | Log: {line.strip()}"
                                    )

        ftp.quit()
    except Exception as e:
        print(f"Erro na auditoria: {e}")


if __name__ == "__main__":
    audit_bases_activity()
