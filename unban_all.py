import os
import sqlite3
import requests
import ftplib
import time
from dotenv import load_dotenv

# Carregar configurações
load_dotenv()
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
DB_PATH = "security.db"


def unban_all():
    print("--- INICIANDO DESBANIMENTO GERAL ---")

    # 1. Limpar Banco de Dados
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "UPDATE infractions SET ban_lifted = 1 WHERE auto_banned = 1 AND ban_lifted = 0"
            )
            count = conn.total_changes
            conn.commit()
            conn.close()
            print(f"[DB] {count} registros marcados como desbanidos.")
        else:
            print("[DB] Arquivo security.db não encontrado no diretório atual.")
    except Exception as e:
        print(f"[DB] Erro: {e}")

    # 2. Limpar API Nitrado (Settings)
    try:
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/settings"
        headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
        # Enviar string vazia para a chave bans
        payload = {"category": "general", "key": "bans", "value": ""}
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            print("[API] Lista de bans Gamertag limpa com sucesso.")
        else:
            print(f"[API] Erro ao limpar: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[API] Erro: {e}")

    # 3. Limpar FTP (ban.txt)
    try:
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, 21, timeout=10)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.set_pasv(True)

        # Tentar caminhos comuns
        paths = [
            "/dayzxb/config",
            "SC/profile",
            "/dayzxb_missions/dayzOffline.chernarusplus",
        ]
        found = False
        for p in paths:
            try:
                ftp.cwd(p)
                # Sobrescrever ban.txt com arquivo vazio
                import io

                empty_file = b""
                ftp.storbinary("STOR ban.txt", io.BytesIO(empty_file))
                print(f"[FTP] ban.txt limpo em {p}")
                found = True
                break
            except Exception:
                continue

        if not found:
            print("[FTP] Arquivo ban.txt não encontrado nos diretórios padrão.")
        ftp.quit()
    except Exception as e:
        print(f"[FTP] Erro: {e}")

    # 4. Reiniciar Servidor
    try:
        print("[NITRADO] Solicitando reinício do servidor para aplicar mudanças...")
        restart_url = (
            f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
        )
        headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
        resp = requests.post(restart_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            print("[NITRADO] Comando de reinício enviado com sucesso.")
        else:
            print(f"[NITRADO] Erro ao reiniciar: {resp.text}")
    except Exception as e:
        print(f"[NITRADO] Erro ao reiniciar: {e}")

    print("--- PROCESSO CONCLUÍDO ---")


if __name__ == "__main__":
    unban_all()
