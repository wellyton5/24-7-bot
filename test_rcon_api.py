import requests
import os
import json
from dotenv import load_dotenv

# Carrega as credenciais da VPS
load_dotenv("/home/ubuntu/24-7-Bot/.env")
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")


def test_broadcast(message):
    # Endpoint de comando RCON via Nitrado API
    url = (
        f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/app_server/command"
    )
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

    # 'say -1' é o comando padrão de RCON para DayZ
    payload = {"command": f"say -1 {message}"}

    print(f"Enviando comando: say -1 {message}")

    try:
        response = requests.post(url, headers=headers, data=payload)
        print(f"Status Code: {response.status_code}")
        print("Resposta da API:")
        print(json.dumps(response.json(), indent=4))
        return response.json()
    except Exception as e:
        print(f"Erro ao enviar comando: {e}")
        return None


if __name__ == "__main__":
    # Teste solicitado pelo usuário
    test_broadcast("SE VOCE ESTA VENDO ESCREVA NO GRUPO: ADM EU VI")

    # Teste 2: Comando 'say' (frequentemente desativado em consoles, mas vale o teste)
    # payload_say = {'command': f'say -1 "TESTE DE CHAT REALTIME"'}
    # requests.post(url, headers=headers, data=payload_say)
