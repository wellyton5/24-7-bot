#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para diagnosticar por que o bot não está monitorando logs"""

import sys
import os

# Testar imports
print("=" * 60)
print("DIAGNÓSTICO DO BOT 24/7")
print("=" * 60)

print("\n1. Testando imports...")
try:
    import discord

    print("✅ discord.py importado")
except Exception as e:
    print(f"❌ Erro ao importar discord: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    print("✅ dotenv importado")
except Exception as e:
    print(f"❌ Erro ao importar dotenv: {e}")
    sys.exit(1)

try:
    import database

    print("✅ database importado")
except Exception as e:
    print(f"❌ Erro ao importar database: {e}")

try:
    from ftp_helpers import connect_ftp

    print("✅ ftp_helpers importado")
except Exception as e:
    print(f"❌ Erro ao importar ftp_helpers: {e}")

# Testar .env
print("\n2. Testando .env...")
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")

if TOKEN:
    print(f"✅ DISCORD_TOKEN configurado ({len(TOKEN)} chars)")
else:
    print("❌ DISCORD_TOKEN não encontrado")

if FTP_HOST:
    print(f"✅ FTP_HOST configurado: {FTP_HOST}")
else:
    print("❌ FTP_HOST não encontrado")

if FTP_USER:
    print(f"✅ FTP_USER configurado: {FTP_USER}")
else:
    print("❌ FTP_USER não encontrado")

# Testar conexão FTP
print("\n3. Testando conexão FTP...")
try:
    ftp = connect_ftp()
    if ftp:
        print("✅ Conexão FTP estabelecida!")
        try:
            ftp.quit()
        except:
            pass
    else:
        print("❌ Falha ao conectar FTP (retornou None)")
except Exception as e:
    print(f"❌ Erro ao conectar FTP: {e}")

# Testar banco de dados
print("\n4. Testando banco de dados...")
try:
    database.init_db()
    print("✅ Banco de dados inicializado")

    import sqlite3

    conn = sqlite3.connect("security.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM bases_security")
    bases = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM item_limits")
    items = cur.fetchone()[0]
    conn.close()

    print(f"   📊 Bases: {bases}, Itens: {items}")
except Exception as e:
    print(f"❌ Erro no banco: {e}")

print("\n" + "=" * 60)
print("DIAGNÓSTICO COMPLETO")
print("=" * 60)
