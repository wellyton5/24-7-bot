import database
import sqlite3

# ID do usuário (baseado no ADMIN_WHITELIST do .env)
USER_ID = "831391383981522964"
GAMERTAG = "BRAZIL555TEXAS"


def manual_link():
    print(f"--- VINCULANDO GAMERTAG MANUALMENTE ---")
    try:
        # Tentar vincular
        database.link_gamertag(USER_ID, GAMERTAG)
        print(f"[V] Sucesso: {USER_ID} -> {GAMERTAG}")

        # Verificar se salvou mesmo
        conn = sqlite3.connect("security.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM discord_links_247 WHERE discord_id = ?", (USER_ID,))
        row = cur.fetchone()
        conn.close()

        if row:
            print(f"[V] Confirmado no DB: {row}")
        else:
            print("[X] Erro: Não encontrado no DB após o link.")

    except Exception as e:
        print(f"[X] Erro durante o vínculo: {e}")


if __name__ == "__main__":
    manual_link()
