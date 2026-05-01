import os, requests
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('NITRADO_TOKEN')
SERVICE = os.getenv('SERVICE_ID')
url = f'https://api.nitrado.net/services/{SERVICE}/gameservers/restart'
headers = {'Authorization': f'Bearer {TOKEN}'}
r = requests.post(url, headers=headers)
print(f'Status: {r.status_code}, Resposta: {r.text}')
