import requests, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def restart_server():
    try:
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
        headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
        r = requests.post(url, headers=headers)
        print(f"Restart Response: {r.json()}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    restart_server()
