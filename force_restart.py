import requests
import os
from dotenv import load_dotenv

load_dotenv()

NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def restart():
    if not NITRADO_TOKEN or not SERVICE_ID:
        print("Erro: NITRADO_TOKEN ou SERVICE_ID não encontrados no .env")
        return

    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

    print(f"Enviando comando de restart para o Service ID: {SERVICE_ID}...")
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            print("SUCESSO: Comando de reinício enviado!")
        else:
            print(f"⚠️ API respondeu com erro: {data}")
    else:
        print(f"❌ ERRO HTTP {response.status_code}: {response.text}")


if __name__ == "__main__":
    restart()
