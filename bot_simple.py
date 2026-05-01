#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 24/7 - Versão Simplificada e Funcional
Monitoramento de logs do servidor DayZ via FTP
"""

import os
import io
import re
import json
import sqlite3
from datetime import datetime
from ftplib import FTP
from dotenv import load_dotenv
import discord
from discord.ext import tasks

load_dotenv()

# Configurações
TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

# Estado global
current_log_file = ""
last_byte_offset = 0

# Cliente Discord
intents = discord.Intents.default()
client = discord.Client(intents=intents)


def init_db():
    """Inicializa banco de dados"""
    conn = sqlite3.connect("security.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bases_security (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_gamertag TEXT NOT NULL,
            coord_x REAL,
            coord_z REAL,
            radius REAL DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS item_limits (
            gamertag TEXT NOT NULL,
            item_type TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (gamertag, item_type)
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] ✅ Banco inicializado")


def connect_ftp():
    """Conecta ao FTP"""
    try:
        ftp = FTP(FTP_HOST, timeout=10)
        ftp.login(FTP_USER, FTP_PASS)
        return ftp
    except Exception as e:
        print(f"[FTP] ❌ Erro: {e}")
        return None


def find_latest_log(ftp):
    """Encontra o log .adm mais recente"""
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            files = ftp.nlst()
            adm_files = [f for f in files if f.lower().endswith(".adm")]
            if adm_files:
                adm_files.sort()
                return f"{path}/{adm_files[-1]}"
        except:
            continue
    return None


def is_garden(item):
    """Detecta gardens"""
    keywords = ["garden", "greenhouse", "planting", "vegetable", "plot", "farming"]
    return any(k in item.lower() for k in keywords)


def is_fireplace(item):
    """Detecta fireplaces"""
    keywords = ["fireplace", "oven", "stove", "campfire", "fire"]
    item_lower = item.lower()
    if "barrel" in item_lower and "hole" in item_lower:
        return True
    return any(k in item_lower for k in keywords)


def increment_item(gamertag, item_type):
    """Incrementa contador de item"""
    conn = sqlite3.connect("security.db")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO item_limits (gamertag, item_type, count, last_updated)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(gamertag, item_type) DO UPDATE SET
        count = count + 1,
        last_updated = CURRENT_TIMESTAMP
    """,
        (gamertag, item_type),
    )
    conn.commit()

    cur.execute(
        "SELECT count FROM item_limits WHERE gamertag = ? AND item_type = ?",
        (gamertag, item_type),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def parse_log_line(line):
    """Processa linha de log"""
    try:
        # Detectar "placed"
        if "placed" in line.lower():
            # Extrair player
            player_match = re.search(r'Player "([^"]+)"', line)
            if not player_match:
                return

            player = player_match.group(1)

            # Extrair item
            placed_match = re.search(r"placed\s+([^<\n]+)", line, re.IGNORECASE)
            if not placed_match:
                return

            item = placed_match.group(1).strip()

            # Verificar se é garden ou fireplace
            if is_garden(item) or is_fireplace(item):
                count = increment_item(player, item)
                item_type = "plantação" if is_garden(item) else "fogueira"

                print(f"[DETECT] {player}: {count}x {item} ({item_type})")

                if count > 2:
                    print(f"[ALERT] ⚠️ {player} excedeu limite de {item_type}s!")
                    # Aqui você pode adicionar notificação Discord se quiser

    except Exception as e:
        print(f"[PARSE] Erro: {e}")


@tasks.loop(seconds=15)
async def monitor_logs():
    """Loop de monitoramento"""
    global last_byte_offset, current_log_file

    print("[MONITOR] Verificando logs...")

    ftp = connect_ftp()
    if not ftp:
        return

    try:
        # Encontrar log mais recente
        latest = find_latest_log(ftp)
        if not latest:
            print("[MONITOR] Nenhum log encontrado")
            return

        # Se mudou o arquivo, resetar offset
        if latest != current_log_file:
            print(f"[MONITOR] Novo log: {latest}")
            current_log_file = latest
            last_byte_offset = 0

        # Verificar tamanho
        ftp.voidcmd("TYPE I")
        size = ftp.size(current_log_file)

        # Se resetou (wipe), zerar offset
        if size < last_byte_offset:
            print("[MONITOR] Log resetado (wipe)")
            last_byte_offset = 0

        # Se há conteúdo novo
        if size > last_byte_offset:
            diff = size - last_byte_offset
            print(f"[MONITOR] Lendo {diff} bytes novos...")

            # Ler conteúdo novo
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {current_log_file}", bio.write, rest=last_byte_offset)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            # Processar linhas
            for line in content.split("\n"):
                if line.strip():
                    parse_log_line(line)

            last_byte_offset = size

        ftp.quit()

    except Exception as e:
        print(f"[MONITOR] Erro: {e}")
        try:
            ftp.quit()
        except:
            pass


@client.event
async def on_ready():
    print(f"[BOT] ✅ Conectado: {client.user}")
    print("[BOT] Inicializando banco...")
    init_db()
    print("[BOT] Iniciando monitoramento...")
    monitor_logs.start()
    print("[BOT] 🚀 Bot operacional!")


if __name__ == "__main__":
    print("[MAIN] Iniciando bot 24/7 simplificado...")
    client.run(TOKEN)
