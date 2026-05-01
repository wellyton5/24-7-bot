import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()
t = os.getenv("NITRADO_TOKEN")
s = os.getenv("SERVICE_ID")


def audit_bans():
    print("--- RELATÓRIO DE BANIMENTOS ATIVOS ---")

    # 1. Verificar API Nitrado
    try:
        url = f"https://api.nitrado.net/services/{s}/gameservers/settings"
        h = {"Authorization": f"Bearer {t}"}
        r = requests.get(url, headers=h, timeout=15)
        bans_raw = r.json()["data"]["settings"]["general"]["bans"]
        bans_list = [b.strip() for b in bans_raw.split("\n") if b.strip()]
        print(f"Nitrado (Gamertags): {len(bans_list)} bans")
        if bans_list:
            print(f"Lista: {bans_list}")
    except Exception as e:
        print(f"Erro Nitrado: {e}")

    # 2. Verificar Banco de Dados
    try:
        conn = sqlite3.connect("security.db")
        cur = conn.cursor()
        cur.execute(
            "SELECT gamertag, infraction_type, detected_at FROM infractions WHERE ban_lifted = 0"
        )
        active_db_bans = cur.fetchall()
        print(f"Banco de Dados: {len(active_db_bans)} bans ativos")
        for b in active_db_bans:
            print(f" - {b[0]} ({b[1]}) em {b[2]}")
        conn.close()
    except Exception as e:
        print(f"Erro DB: {e}")

    # 3. Verificar FTP (XUIDs)
    # Como já sabemos o caminho, vamos apenas reportar o status se possível
    print("--- FIM DO RELATÓRIO ---")


if __name__ == "__main__":
    audit_bans()
