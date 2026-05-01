import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def fix_lucasguto():
    db = "security.db"
    if not os.path.exists(db):
        print("Erro: security.db não encontrado na pasta atual.")
        return

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # 1. Lista de Gamertags associadas ao hardware do LucasGuto (conforme diagnosticado anteriormente)
    gts = [
        "lucasguto7249",
        "lucasguto724(4)",
        "lucasguto724(2)",
        "lucasguto724(1)",
        "Rafa52119",
        "zhGAMEPASSx",
        "nGamepass6838",
        "WizenStone86899",
    ]

    # 2. Atualizar Banco de Dados
    print(f"Limpando infrações no DB para o grupo: {gts}")
    # Usando LIKE para garantir que pegamos variações se necessário, mas aqui usaremos IN para precisão
    cur.execute(
        "UPDATE infractions SET ban_lifted = 1 WHERE gamertag IN ({})".format(
            ",".join(["?"] * len(gts))
        ),
        gts,
    )
    conn.commit()
    print(f"Registros atualizados no banco de dados.")

    # 3. Limpar na API do Nitrado
    try:
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/settings"
        headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

        # Ler bans atuais
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

        current_bans_str = data["data"]["settings"]["general"]["bans"]
        current_bans = [b.strip() for b in current_bans_str.split("\n") if b.strip()]

        # Filtrar removendo os do grupo lucasguto
        new_bans = [
            b for b in current_bans if not any(gt.lower() in b.lower() for gt in gts)
        ]

        if len(current_bans) != len(new_bans):
            print(
                f"Atualizando Nitrado API. Bans antes: {len(current_bans)}, depois: {len(new_bans)}"
            )
            requests.post(
                url,
                headers=headers,
                json={
                    "category": "general",
                    "key": "bans",
                    "value": "\r\n".join(new_bans),
                },
            )
            print("Lista de banimentos enviada para o Nitrado.")
        else:
            print("Nenhum dos nomes estava na lista de banimento da API do Nitrado.")

    except Exception as e:
        print(f"Erro ao interagir com a API do Nitrado: {e}")

    conn.close()
    print("Sucesso. O grupo lucasguto foi desbanido no DB e na API.")


if __name__ == "__main__":
    fix_lucasguto()
