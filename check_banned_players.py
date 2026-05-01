import os
import sqlite3
from ftplib import FTP
from io import BytesIO
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
DB_PATH = "/home/ubuntu/24-7-Bot/bigode_unified.db"


def get_current_players():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        latest_file = None
        for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
            try:
                ftp.cwd(path)
                files = ftp.nlst()
                adm_files = [f for f in files if f.lower().endswith(".adm")]
                if adm_files:
                    latest_file = path + "/" + sorted(adm_files)[-1]
                    break
            except:
                continue

        if not latest_file:
            return []

        bio = BytesIO()
        ftp.retrbinary(f"RETR {latest_file}", bio.write)
        ftp.quit()
        content = bio.getvalue().decode("utf-8", errors="ignore")

        players = set()
        for line in content.splitlines():
            # Example: 21:40:05 | Player "Nome do Jogador" (id=ABCD...) connected
            # or: 21:40:05 | Player "Nome do Jogador" connected
            if "connected" in line.lower() and '"' in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    players.add(parts[1])
            if "disconnected" in line.lower() and '"' in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    name = parts[1]
                    if name in players:
                        players.remove(name)
        return list(players)
    except Exception as e:
        return [f"ERROR:{e}"]


def check_bans():
    players = get_current_players()
    print(f"Jogadores Online agora: {players}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Buscar infratores recentes (coluna correta é 'gamertag')
    cur.execute(
        "SELECT gamertag, description, detected_at FROM infractions ORDER BY detected_at DESC LIMIT 200"
    )
    infractions = cur.fetchall()

    # Buscar banimentos ativos
    cur.execute("SELECT identifier, reason FROM security_bans WHERE is_active = 1")
    bans = cur.fetchall()

    # Buscar conexões recentes
    cur.execute(
        "SELECT gamertag, connected_at FROM connection_logs ORDER BY connected_at DESC LIMIT 200"
    )
    conn_logs = cur.fetchall()

    print("\n--- RESULTADO DA ANÁLISE ---")
    flagged = []

    # 1. Verificar jogadores ONLINE agora
    for p in players:
        # Check against infractions
        for inf in infractions:
            if p.lower() == str(inf[0]).lower():
                flagged.append(
                    f"🚩 ALERTA: {p} está ONLINE agora. Possui infração: {inf[1]} em {inf[2]}"
                )

        # Check against bans
        for ban in bans:
            if p.lower() == str(ban[0]).lower():
                flagged.append(
                    f"⚠️ CRÍTICO: {p} está ONLINE agora e consta como BANIDO por: {ban[1]}"
                )

    # 2. Verificar histórico RECENTE
    for log_name, log_time in conn_logs:
        # Check against infractions
        for inf_name, inf_desc, inf_time in infractions:
            if log_name.lower() == inf_name.lower():
                flagged.append(
                    f"👤 HISTÓRICO: {log_name} jogou em {log_time}. Possui infração registrada em {inf_time}"
                )

        # Check against bans
        for ban_id, ban_reason in bans:
            if log_name.lower() == str(ban_id).lower():
                flagged.append(
                    f"⛔ HISTÓRICO: {log_name} (BANIDO) jogou em {log_time}! Motivo: {ban_reason}"
                )

    cur.execute(
        "SELECT gamertag, connected_at FROM connection_logs ORDER BY connected_at DESC LIMIT 10"
    )
    recent_all = cur.fetchall()
    print("\n--- PROVA DE ATIVIDADE (Últimas 10 conexões registradas) ---")
    if recent_all:
        for r in recent_all:
            print(f"✅ Registro: {r[0]} entrou em {r[1]}")
    else:
        print("ℹ️ Nenhuma conexão registrada no banco de dados nas tabelas unificadas.")

    if not flagged:
        print(
            "✅ Nenhum jogador banido ou com infrações graves foi detectado no servidor recentemente."
        )
    else:
        # Remover duplicados (mesmo jogador várias vezes)
        unique_flagged = list(set(flagged))
        for f in sorted(unique_flagged):
            print(f)


if __name__ == "__main__":
    check_bans()
