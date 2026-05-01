import sqlite3
import os

db_path = "/home/ubuntu/24-7-Bot/security.db"


def query_logs():
    if not os.path.exists(db_path):
        print("Banco de dados não encontrado.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Procurar por qualquer coisa relacionada a veículos
        cur.execute(
            "SELECT gamertag, action, timestamp FROM security_logs_247 WHERE action LIKE '%vehicle%' OR action LIKE '%truck%' OR action LIKE '%car%' ORDER BY timestamp DESC LIMIT 30"
        )
        rows = cur.fetchall()
        if rows:
            print("--- LOGS DE VEÍCULOS ENCONTRADOS ---")
            for r in rows:
                print(f"[{r[2]}] {r[0]}: {r[1]}")
        else:
            print("Nenhum log de veículo encontrado.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    query_logs()
