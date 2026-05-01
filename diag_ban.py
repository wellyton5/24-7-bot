import sqlite3
import os


def diag():
    db = "security.db"
    if not os.path.exists(db):
        print("DB not found")
        return

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    print("--- BASES RELACIONADAS A YASMIN ---")
    cur.execute(
        "SELECT id, owner_gamertag, x, z, created_at FROM bases_security WHERE owner_gamertag LIKE '%Yasmin%'"
    )
    bases = cur.fetchall()
    for b in bases:
        print(f"Base ID: {b[0]} | Owner: {b[1]} | Coord: {b[2]}, {b[3]} | Data: {b[4]}")

        # Verificar permissões desta base
        cur.execute(
            "SELECT gamertag_authorized, authorized_by FROM base_permissions WHERE base_id = ?",
            (b[0],),
        )
        perms = cur.fetchall()
        if perms:
            print(f"  Permissões: {perms}")
        else:
            print("  Sem permissões extras.")

    print("\n--- INFRAÇÕES RECENTES ---")
    cur.execute(
        "SELECT id, gamertag, infraction_type, detected_at, description FROM infractions WHERE detected_at > datetime('now', '-1 hour')"
    )
    infrs = cur.fetchall()
    for i in infrs:
        print(f"ID: {i[0]} | GT: {i[1]} | Tipo: {i[2]} | Data: {i[3]} | Desc: {i[4]}")

    print("\n--- IDENTIDADES (ALTS) ---")
    # Tentar ver se YasmimL03 e Yasmin035083 compartilham o mesmo IP ou Dispositivo
    cur.execute("SELECT * FROM player_identities WHERE gamertag LIKE '%Yasmin%'")
    idents = cur.fetchall()
    for idt in idents:
        print(f"GT: {idt[0]} | XUID: {idt[1]} | IP: {idt[2]} | Device: {idt[3]}")

    conn.close()


if __name__ == "__main__":
    diag()
