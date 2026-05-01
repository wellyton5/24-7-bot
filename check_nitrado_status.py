import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
T = os.getenv("NITRADO_TOKEN")
S = os.getenv("SERVICE_ID")


def check_status():
    url = f"https://api.nitrado.net/services/{S}/gameservers"
    headers = {"Authorization": f"Bearer {T}"}
    r = requests.get(url, headers=headers)
    data = r.json()["data"]["gameserver"]
    print(f"Status: {data['status']}")
    print(f"Query Name: {data['query']['server_name']}")
    print(
        f"Player Count: {data['query']['player_current']}/{data['query']['player_max']}"
    )
    print(f"Server Time: {datetime.now()}")


if __name__ == "__main__":
    check_status()
