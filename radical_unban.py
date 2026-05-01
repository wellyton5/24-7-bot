import os
import io
import sqlite3
import requests
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def deep_clean_all_bans():
    print("=== INICIANDO LIMPEZA PROFUNDA DE BANS ===")

    # 1. Limpar Banco de Dados
    try:
        conn = sqlite3.connect("security.db")
        cur = conn.cursor()
        print("Marcando todas as infrações como levantadas no DB...")
        cur.execute("UPDATE infractions SET ban_lifted = 1")
        conn.commit()
        conn.close()
        print("[OK] Banco de Dados limpo.")
    except Exception as e:
        print(f"[ERRO] Falha ao limpar DB: {e}")

    # 2. Limpar arquivo ban.txt via FTP
    try:
        print(f"Conectando ao FTP: {FTP_HOST}...")
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        ban_path = "/dayzxb/config/ban.txt"
        print(f"Sobrescrevendo {ban_path} com arquivo vazio...")

        empty_ban = io.BytesIO(b"")
        ftp.storbinary(f"STOR {ban_path}", empty_ban)

        ftp.quit()
        print("[OK] ban.txt limpo (0 XUIDs).")
    except Exception as e:
        print(f"[ERRO] Falha ao limpar ban.txt via FTP: {e}")

    # 3. Limpar Nitrado API (General Bans)
    try:
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/settings"
        headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

        print("Limpando lista de bans na API do Nitrado...")
        payload = {"category": "general", "key": "bans", "value": ""}
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            print("[OK] API Nitrado limpa (0 Gamertags).")
        else:
            print(f"[ERRO] Falha na API Nitrado: {r.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao interagir com a API: {e}")

    # 4. Comandar RESTART do servidor Nitrado (Obrigatório para ban.txt)
    try:
        print("Enviando comando de RESTART para o servidor Nitrado...")
        restart_url = (
            f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
        )
        r = requests.post(restart_url, headers=headers)
        if r.status_code == 200:
            print("[OK] Servidor está reiniciando para aplicar a limpeza.")
        else:
            print(f"[ERRO] Falha ao solicitar restart: {r.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao solicitar restart: {e}")

    print("=== LIMPEZA CONCLUÍDA ===")


if __name__ == "__main__":
    deep_clean_all_bans()
