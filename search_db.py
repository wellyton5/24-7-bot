import sqlite3
import os


def search_gt(pattern):
    db = "security.db"
    if not os.path.exists(db):
        return

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    print(f"Buscando por: {pattern}")
    cur.execute(
        "SELECT gamertag FROM player_identities WHERE gamertag LIKE ?",
        (f"%{pattern}%",),
    )
    res = cur.fetchall()
    for r in res:
        print(f" - {r[0]}")

    cur.execute(
        "SELECT gamertag FROM discord_links_247 WHERE gamertag LIKE ?",
        (f"%{pattern}%",),
    )
    res2 = cur.fetchall()
    for r in res2:
        print(f" - {r[0]} (Vinculado)")

    conn.close()


if __name__ == "__main__":
    import sys

    search_gt(sys.argv[1] if len(sys.argv) > 1 else "wizen")
