import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("NITRADO_TOKEN")
service_id = os.getenv("SERVICE_ID")

url = f"https://api.nitrado.net/services/{service_id}/gameservers"
headers = {"Authorization": f"Bearer {token}"}

try:
    r = requests.get(url, headers=headers, timeout=15)
    data = r.json()
    status = data["data"]["gameserver"]["status"]
    print(status)
except Exception as e:
    print(f"error: {e}")
