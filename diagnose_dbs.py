import sqlite3
import json
import os


def check_db(path, name):
    if not os.path.exists(path):
        print(f"--- {name} ({path}) NAO EXISTE ---")
        return
    print(f"--- ANALISE DE {name} ({path}) ---")
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        for table in tables:
            tname = table[0]
            cur.execute(f"PRAGMA table_info({tname})")
            cols = [c[1] for c in cur.fetchall()]
            cur.execute(f"SELECT COUNT(*) FROM {tname}")
            count = cur.fetchone()[0]
            print(f"Tabela: {tname} | Colunas: {cols} | Registros: {count}")
            if tname in ["connection_logs", "player_identities", "infractions"]:
                cur.execute(
                    f"SELECT * FROM {tname} ORDER BY (case when ROWID then ROWID else 1 end) DESC LIMIT 3"
                )
                print(f"  Últimos 3: {cur.fetchall()}")
        conn.close()
    except Exception as e:
        print(f"Erro ao ler {path}: {e}")


def check_json(path, name):
    if not os.path.exists(path):
        print(f"--- {name} ({path}) NAO EXISTE ---")
        return
    print(f"--- ANALISE DE {name} ({path}) ---")
    try:
        with open(path, "r") as f:
            data = json.load(f)
            print(
                f"Tipo: {type(data)} | Registros: {len(data) if hasattr(data, '__len__') else 'N/A'}"
            )
            if isinstance(data, dict) and len(data) > 0:
                first_key = list(data.keys())[0]
                print(f"Exemplo de chave: {first_key}")
                print(f"Exemplo de valor: {data[first_key]}")
    except Exception as e:
        print(f"Erro ao ler {path}: {e}")


if __name__ == "__main__":
    base_dir = "/home/ubuntu/24-7-Bot"
    check_db(f"{base_dir}/bigode_unified.db", "Unified DB")
    check_db(f"{base_dir}/security.db", "Security DB")
    check_db(f"{base_dir}/pvp_events.db", "PVP Events DB")
    check_json(f"{base_dir}/players_db.json", "Players JSON")
    check_json(f"{base_dir}/links.json", "Links JSON")
    check_json(f"{base_dir}/economy.json", "Economy JSON")
    check_json(f"{base_dir}/clans.json", "Clans JSON")
