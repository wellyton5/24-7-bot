import requests
import os
from dotenv import load_dotenv

load_dotenv()

NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def check_status():
    if not NITRADO_TOKEN or not SERVICE_ID:
        print("Erro: Credenciais ausentes.")
        return

    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers"
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            gs = data["data"]["gameserver"]
            q = gs.get("query", {})
            status = gs.get("status", "unknown")
            players = q.get("player_current", 0)
            max_p = q.get("player_max", 0)
            print(f"Status: {status}")
            print(f"Jogadores: {players}/{max_p}")
        else:
            print(f"Erro HTTP {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    check_status()
