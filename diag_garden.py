import sqlite3
import os
import re


def check_gardens():
    db = "security.db"
    if not os.path.exists(db):
        print("Erro: security.db não encontrado.")
        return

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    print("--- INFRAÇÕES DE GARDEN/PLANTING (Últimas 24h) ---")
    cur.execute("""
        SELECT id, gamertag, infraction_type, description, detected_at, ban_lifted 
        FROM infractions 
        WHERE (infraction_type LIKE '%garden%' OR description LIKE '%garden%' OR description LIKE '%planta%')
        AND detected_at > datetime('now', '-1 day')
        ORDER BY detected_at DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            status = "LEVANTADO" if r[5] else "ATIVO"
            print(
                f"ID: {r[0]} | GT: {r[1]} | Tipo: {r[2]} | Status: {status} | Data: {r[4]}"
            )
            print(f"  Desc: {r[3]}")
    else:
        print("Nenhuma infração recente encontrada no banco de dados.")

    print(
        "\n--- ANALISANDO LOGS RECENTES (/home/ubuntu/24-7-Bot/bot_247.log ou journalctl) ---"
    )
    # Tentar buscar no journalctl por eventos de plantação processados pelo bot
    print("Buscando 'GardenPlot' ou 'Planted' no journalctl...")
    os.system(
        "sudo journalctl -u 24-7-bot.service -n 500 | grep -iE 'garden|planted|constru' | tail -n 20"
    )

    conn.close()


if __name__ == "__main__":
    check_gardens()
