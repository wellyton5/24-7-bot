import requests, os, json
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def debug_tasks():
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
    try:
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/tasks"
        response = requests.get(url, headers=headers)
        data = response.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_tasks()
