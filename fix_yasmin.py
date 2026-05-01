import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def fix_yasmin():
    db = "security.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # 1. Lista de Gamertags para desbanir
    gts = [
        "YasmimL03",
        "Yasmin035083",
        "Aquino7986",
        "F Aquino93(3)",
        "Aquino7986(1)",
        "F Aquino93",
    ]

    # 2. Atualizar Banco de Dados
    print(f"Limpando infrações no DB para: {gts}")
    cur.execute(
        "UPDATE infractions SET ban_lifted = 1 WHERE gamertag IN ({})".format(
            ",".join(["?"] * len(gts))
        ),
        gts,
    )
    conn.commit()

    # 3. Autorizar YasmimL03 na base 58 (de Yasmin035083)
    print("Autorizando YasmimL03 na base 58...")
    cur.execute(
        "INSERT OR IGNORE INTO base_permissions (base_id, gamertag_authorized, authorized_by) VALUES (58, 'YasmimL03', 'SYSTEM_FIX')"
    )
    conn.commit()
    conn.close()

    # 4. Limpar na API do Nitrado
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/settings"
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

    # Ler bans atuais
    r = requests.get(url, headers=headers)
    current_bans = r.json()["data"]["settings"]["general"]["bans"].split("\n")

    # Filtrar removendo os das Yasmins
    new_bans = [
        b.strip()
        for b in current_bans
        if b.strip() and not any(gt.lower() in b.lower() for gt in gts)
    ]

    print(
        f"Atualizando Nitrado API. Bans antes: {len(current_bans)}, depois: {len(new_bans)}"
    )
    requests.post(
        url,
        headers=headers,
        json={"category": "general", "key": "bans", "value": "\r\n".join(new_bans)},
    )

    # 5. Reiniciar o bot para recarregar estado
    print("Sucesso. O bot já deve parar de expulsá-las.")


if __name__ == "__main__":
    fix_yasmin()
