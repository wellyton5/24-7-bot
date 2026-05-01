import sqlite3
import os


def check_account(gt):
    db = "security.db"
    if not os.path.exists(db):
        print("Erro: security.db não encontrado.")
        return

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # 1. Identidade
    print(f"--- RELATÓRIO: {gt} ---")
    cur.execute("SELECT * FROM player_identities WHERE gamertag = ?", (gt,))
    ident = cur.fetchone()
    if ident:
        print(
            f"Identidade: GT={ident[0]}, XUID={ident[1]}, IP={ident[2]}, Device={ident[3]}"
        )

        # Alts pelo Device ID
        if ident[3]:
            cur.execute(
                "SELECT gamertag FROM player_identities WHERE device_id = ? AND gamertag != ?",
                (ident[3], gt),
            )
            alts = cur.fetchall()
            print(f"Alts (mesmo Hardware): {[a[0] for a in alts]}")
    else:
        print("Nenhuma identidade encontrada para este nome exato.")

    # 2. Infrações
    cur.execute(
        "SELECT infraction_type, description, detected_at, ban_lifted FROM infractions WHERE gamertag = ?",
        (gt,),
    )
    infrs = cur.fetchall()
    if infrs:
        print("\nHistórico de Infrações:")
        for i in infrs:
            status = "LEVANTADO" if i[3] else "ATIVO"
            print(f" - [{status}] {i[0]} em {i[2]}: {i[1]}")
    else:
        print("\nNenhuma infração registrada.")

    # 3. Vínculo Discord
    cur.execute("SELECT discord_id FROM discord_links_247 WHERE gamertag = ?", (gt,))
    link = cur.fetchone()
    if link:
        print(f"\nDiscord Vinculado: <@{link[0]}>")
    else:
        print("\nSem vínculo de Discord encontrado.")

    conn.close()


if __name__ == "__main__":
    import sys

    gt = sys.argv[1] if len(sys.argv) > 1 else "WizenStone86899"
    check_account(gt)
