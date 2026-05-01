# -*- coding: utf-8 -*-
"""
Sistema de Banimento Automático IMEDIATO - BigodeTexas
Detecta infrações e aplica ban instantâneo via:
  1. FTP ban.txt (XUID — persistente, DayZ server level)
  2. Settings API (Gamertag — bloqueio IMEDIATO, proxy Nitrado)
  3. Restart inteligente (acumulação + cooldown para releitura ban.txt)

Descoberta: a Settings API da Nitrado (POST /settings, key=bans) funciona
como mecanismo de ban em tempo real no proxy/gateway — mesmo método usado
por bots comerciais (Killfeed, Omnipotent, Legion).
"""

import asyncio
import os
import sqlite3
import sys
import time as _time
from datetime import datetime
from ftplib import FTP
from io import BytesIO

import aiohttp
import requests
from dotenv import load_dotenv

# Adicionar raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

# Sincronização desativada para o modo independente 24/7
SYNC_ENABLED = False

load_dotenv()

# Caminho do banco de dados (mesmo security.db usado pelo database.py)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.db")


# ==================== DEDUPLICAÇÃO DE BANS ====================
# Jogadores já banidos nesta sessão — evita spam de infrações duplicadas
# Chave: xuid quando disponível, gamertag.lower() como fallback
_banned_this_session: set = set()


def is_already_banned(gamertag: str, xuid: str = None) -> bool:
    """Retorna True se o jogador já foi banido nesta sessão (evita spam de notificações)."""
    key = xuid if xuid else gamertag.lower()
    return key in _banned_this_session


# ==================== CALLBACKS (resolve dependência circular) ====================
# Setados por main_247.py via set_callbacks() no on_ready()
_restart_fn = None   # restart_nitrado() — reinicia servidor via API Nitrado
_notify_fn = None    # notify_ban() — envia mensagem ao canal de bans no Discord


def set_callbacks(restart_fn=None, notify_fn=None):
    """
    Registra funções de callback do main_247.py.
    Resolve dependência circular: auto_ban_system não importa main_247.py.

    Args:
        restart_fn: async function que reinicia o servidor (restart_nitrado)
        notify_fn: async function que envia mensagem ao Discord (notify_ban)
    """
    global _restart_fn, _notify_fn
    if restart_fn:
        _restart_fn = restart_fn
        print("[AUTO-BAN] Callback restart_fn registrado")
    if notify_fn:
        _notify_fn = notify_fn
        print("[AUTO-BAN] Callback notify_fn registrado")


# ==================== RESTART INTELIGENTE ====================
# Agenda restart após bans para forçar releitura do ban.txt pelo DayZ server.
# A Settings API já bloqueia imediatamente no proxy, mas o restart garante
# que o ban.txt (XUIDs) também seja aplicado pelo gameserver.
_pending_restart = False
_last_restart_time = 0
_pending_ban_names = []
RESTART_ACCUMULATE_SECS = 120   # 2 min — acumula bans antes de reiniciar
RESTART_COOLDOWN_SECS = 900     # 15 min — mínimo entre restarts


async def schedule_restart_for_ban(gamertag: str):
    """
    Agenda restart inteligente após ban.
    - Acumula bans por 2 min (evita restart para cada ban individual)
    - Respeita cooldown de 15 min entre restarts
    - Envia aviso no Discord 30s antes do restart
    """
    global _pending_restart, _pending_ban_names

    _pending_ban_names.append(gamertag)

    if _pending_restart:
        print(
            f"[RESTART] Ban de {gamertag} acumulado — restart já agendado "
            f"({len(_pending_ban_names)} pendentes)"
        )
        return

    _pending_restart = True
    print(f"[RESTART] Restart agendado em {RESTART_ACCUMULATE_SECS}s para aplicar bans...")
    asyncio.ensure_future(_delayed_restart())


async def _delayed_restart():
    """Executa restart após período de acumulação, respeitando cooldown."""
    global _pending_restart, _last_restart_time, _pending_ban_names

    # Espera período de acumulação (2 min)
    await asyncio.sleep(RESTART_ACCUMULATE_SECS)

    # Verificar cooldown
    now = _time.time()
    elapsed = now - _last_restart_time
    if elapsed < RESTART_COOLDOWN_SECS:
        wait_more = RESTART_COOLDOWN_SECS - elapsed
        print(f"[RESTART] Cooldown ativo — aguardando mais {int(wait_more)}s...")
        await asyncio.sleep(wait_more)

    # Captura nomes pendentes e limpa
    names = list(_pending_ban_names)
    _pending_ban_names.clear()
    _pending_restart = False

    if not names:
        print("[RESTART] Nenhum ban pendente — restart cancelado")
        return

    if not _restart_fn:
        print("[RESTART] [X] Callback restart_fn não registrado — restart cancelado")
        return

    # Aviso Discord 30s antes
    if _notify_fn:
        try:
            names_str = ", ".join(names[:5])
            if len(names) > 5:
                names_str += f" (+{len(names) - 5})"
            await _notify_fn(
                f"⚠️ **Restart em 30s** — Aplicando {len(names)} ban(s) "
                f"no servidor: {names_str}"
            )
        except Exception as e:
            print(f"[RESTART] Erro ao notificar Discord: {e}")

    await asyncio.sleep(30)

    # Executar restart
    print(f"[RESTART] Reiniciando servidor para aplicar {len(names)} ban(s)...")
    try:
        result = await _restart_fn()
        _last_restart_time = _time.time()
        if result:
            print("[RESTART] Servidor reiniciado com sucesso")
            if _notify_fn:
                try:
                    await _notify_fn(
                        f"✅ Servidor reiniciado — {len(names)} ban(s) aplicados via ban.txt"
                    )
                except Exception:
                    pass
        else:
            print("[RESTART] Falha ao reiniciar servidor")
    except Exception as e:
        print(f"[RESTART] Erro ao reiniciar: {e}")


# ==================== WHITELIST DE PROTEÇÃO ====================
# XUIDs protegidos - NUNCA serão banidos automaticamente
# Administradores e moderadores do servidor
PROTECTED_XUIDS = [
    "2535405695546273",  # Wellyton (Admin Principal)
    # Adicione outros admins aqui:
    # "1234567890123456",  # Nome do Admin
]


# ==================== TIPOS DE INFRAÇÕES ====================


class InfractionType:
    """Tipos de infrações detectáveis"""

    # CRÍTICAS (Ban Permanente Imediato)
    LAG_MACHINE = "lag_machine"  # Spam de construção (>10 itens/min)
    FLY_HACK = "fly_hack"  # Construção em altura ilegal
    SKY_BASE = "sky_base"  # Base acima de 1000m
    UNDERGROUND_BASE = "underground_base"  # Base abaixo de -10m
    BANNED_ITEM = "banned_item"  # Uso de item proibido (pneus, shelter)
    DUPLICATION = "item_duplication"  # Duplicação de itens (relog rápido)
    SPEED_HACK = "speed_hack"  # Velocidade anormal
    AIMBOT = "aimbot"  # Headshot rate anormal
    WALLHACK = "wallhack"  # Kills através de paredes

    # GRAVES (Ban Imediato - Revisável)
    ALT_ACCOUNT = "alt_account"  # Múltiplas contas mesmo IP
    GARDEN_EXPLOIT = "garden_exploit"  # Construção em jardim
    FIREPLACE_GRIEF = "fireplace_grief"  # Fogueira em base alheia
    RAID_EXPLOIT = "raid_exploit"  # Raid fora do horário permitido
    GLITCH_ABUSE = "glitch_abuse"  # Abuso de bugs do jogo
    TERRITORY_INVASION = "territory_invasion"  # Construção em território alheio

    # CATEGORIAS
    CATEGORIES = {
        "CRÍTICA": [
            LAG_MACHINE,
            FLY_HACK,
            SKY_BASE,
            UNDERGROUND_BASE,
            BANNED_ITEM,
            DUPLICATION,
            SPEED_HACK,
            AIMBOT,
            WALLHACK,
            TERRITORY_INVASION,
        ],
        "GRAVE": [
            ALT_ACCOUNT,
            GARDEN_EXPLOIT,
            FIREPLACE_GRIEF,
            RAID_EXPLOIT,
            GLITCH_ABUSE,
        ],
    }


def ensure_infractions_table():
    """Cria tabela de infrações se não existir"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS infractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gamertag TEXT NOT NULL,
                discord_id TEXT,
                xuid TEXT,
                ip_address TEXT,
                infraction_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT,
                evidence TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auto_banned BOOLEAN DEFAULT 1,
                ban_lifted BOOLEAN DEFAULT 0,
                admin_notes TEXT
            )
        """)

        # Índices para performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gamertag ON infractions(gamertag)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xuid ON infractions(xuid)")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_type ON infractions(infraction_type)"
        )

        conn.commit()
        return True
    except Exception as e:
        print(f"[AUTO-BAN] Erro ao criar tabela de infrações: {e}")
        return False
    finally:
        conn.close()


def record_infraction(
    gamertag,
    infraction_type,
    description,
    evidence=None,
    xuid=None,
    ip_address=None,
    discord_id=None,
):
    """Registra uma infração no banco de dados"""

    # Determinar severidade
    severity = "CRÍTICA"
    for sev, types in InfractionType.CATEGORIES.items():
        if infraction_type in types:
            severity = sev
            break

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO infractions
            (gamertag, discord_id, xuid, ip_address, infraction_type, severity,
             description, evidence, auto_banned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
            (
                gamertag,
                discord_id,
                xuid,
                ip_address,
                infraction_type,
                severity,
                description,
                evidence,
            ),
        )

        conn.commit()
        infraction_id = cur.lastrowid

        print(
            f"[AUTO-BAN] Infração registrada: {gamertag} - {infraction_type} (ID: {infraction_id})"
        )
        return infraction_id

    except Exception as e:
        print(f"[AUTO-BAN] Erro ao registrar infração: {e}")
        return None
    finally:
        conn.close()


# ==================== RATE LIMITING NITRADO API ====================
# A Nitrado tem rate limits não documentados. Requests em sequência rápida
# podem causar IP ban temporário. Usamos semáforo + delay entre requests.
_nitrado_api_semaphore = asyncio.Semaphore(1)  # 1 request por vez
NITRADO_API_DELAY = 1.5  # segundos entre requests à Settings API
_last_api_call_time = 0


async def _rate_limited_delay():
    """Garante delay mínimo entre chamadas à API Nitrado."""
    global _last_api_call_time
    now = _time.time()
    elapsed = now - _last_api_call_time
    if elapsed < NITRADO_API_DELAY:
        wait = NITRADO_API_DELAY - elapsed
        await asyncio.sleep(wait)
    _last_api_call_time = _time.time()


def _parse_bans_string(bans_str):
    """Extrai set de gamertags de uma string de bans (qualquer separador)."""
    return set(
        b.strip()
        for b in bans_str.replace("\r\n", "\r").replace("\n", "\r").split("\r")
        if b.strip()
    )


# ==================== SETTINGS API BAN (BLOQUEIO IMEDIATO) ====================


async def ban_player_settings_api(gamertag):
    """
    Adiciona gamertag à banlist via Settings API da Nitrado.

    BLOQUEIO IMEDIATO — atua no proxy/gateway Nitrado, sem necessidade de restart.
    Método confirmado: mesmo usado por bots comerciais (Killfeed, Omnipotent, Legion).
    Confirmado na Issue #18 do NitrAPI oficial.

    Fluxo:
      1. GET /settings → ler lista atual de bans
      2. Verificar se gamertag já está na lista
      3. Adicionar gamertag à lista
      4. POST /settings → key=bans, value=lista atualizada
      5. VERIFICAÇÃO: GET novamente para confirmar (anti POST-fantasma)

    Rate limiting: semáforo + delay de 1.5s entre requests.
    """
    nitrado_token = os.getenv("NITRADO_TOKEN")
    service_id = os.getenv("SERVICE_ID")

    if not nitrado_token or not service_id:
        print("[AUTO-BAN] [X] Credenciais Nitrado não configuradas para Settings API")
        return False

    base_url = f"https://api.nitrado.net/services/{service_id}/gameservers/settings"
    headers = {"Authorization": f"Bearer {nitrado_token}"}

    async with _nitrado_api_semaphore:  # Uma request por vez
        try:
            async with aiohttp.ClientSession() as session:
                # 1. GET settings → ler bans atuais (com rate limit)
                await _rate_limited_delay()
                async with session.get(
                    base_url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        print(f"[AUTO-BAN] [X] Settings API GET HTTP {resp.status}")
                        return False
                    data = await resp.json()

                # 2. Extrair lista atual de bans
                current_bans_str = (
                    data.get("data", {})
                    .get("settings", {})
                    .get("general", {})
                    .get("bans", "")
                )

                current_bans = _parse_bans_string(current_bans_str)

                # 3. Verificar se já está na lista
                if gamertag in current_bans:
                    print(f"[AUTO-BAN] [OK] {gamertag} já está na banlist Settings API")
                    return True

                # 4. Adicionar e POST (com rate limit)
                current_bans.add(gamertag)
                new_value = "\r\n".join(sorted(current_bans))

                post_data = {
                    "category": "general",
                    "key": "bans",
                    "value": new_value,
                }

                await _rate_limited_delay()
                async with session.post(
                    base_url, headers=headers, json=post_data,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        print(f"[AUTO-BAN] [X] Settings API POST HTTP {resp.status}")
                        return False
                    result = await resp.json()
                    if result.get("status") != "success":
                        print(f"[AUTO-BAN] [X] Settings API POST resposta: {result}")
                        return False

                # 5. VERIFICAÇÃO PÓS-BAN: GET para confirmar (anti POST-fantasma)
                # A Nitrado pode retornar 200 sem executar a ação.
                await _rate_limited_delay()
                async with session.get(
                    base_url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        verify_data = await resp.json()
                        verify_bans_str = (
                            verify_data.get("data", {})
                            .get("settings", {})
                            .get("general", {})
                            .get("bans", "")
                        )
                        verify_bans = _parse_bans_string(verify_bans_str)

                        if gamertag in verify_bans:
                            print(
                                f"[AUTO-BAN] [V] Settings API: {gamertag} "
                                f"BLOQUEADO + VERIFICADO ({len(verify_bans)} na lista)"
                            )
                            return True
                        else:
                            print(
                                f"[AUTO-BAN] [!] POST-FANTASMA: {gamertag} não apareceu "
                                f"na lista após POST 200. Nitrado não executou."
                            )
                            return False
                    else:
                        # Verificação falhou, mas POST retornou 200 — considerar OK
                        print(
                            f"[AUTO-BAN] [V] Settings API: {gamertag} BLOQUEADO "
                            f"(verificação HTTP {resp.status}, POST foi 200)"
                        )
                        return True

        except Exception as e:
            print(f"[AUTO-BAN] [X] Settings API erro: {e}")

    return False


async def unban_player_settings_api(gamertag):
    """
    Remove gamertag da banlist via Settings API da Nitrado.
    Para uso com comando !unban — remove bloqueio imediato do proxy.
    Com rate limiting e verificação pós-remoção.
    """
    nitrado_token = os.getenv("NITRADO_TOKEN")
    service_id = os.getenv("SERVICE_ID")

    if not nitrado_token or not service_id:
        print("[UNBAN] [X] Credenciais Nitrado não configuradas")
        return False

    base_url = f"https://api.nitrado.net/services/{service_id}/gameservers/settings"
    headers = {"Authorization": f"Bearer {nitrado_token}"}

    async with _nitrado_api_semaphore:
        try:
            async with aiohttp.ClientSession() as session:
                # 1. GET settings (com rate limit)
                await _rate_limited_delay()
                async with session.get(
                    base_url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        print(f"[UNBAN] [X] Settings API GET HTTP {resp.status}")
                        return False
                    data = await resp.json()

                # 2. Extrair lista e filtrar
                current_bans_str = (
                    data.get("data", {})
                    .get("settings", {})
                    .get("general", {})
                    .get("bans", "")
                )

                current_bans = _parse_bans_string(current_bans_str)

                if gamertag not in current_bans:
                    print(f"[UNBAN] {gamertag} não está na banlist Settings API")
                    return True

                # 3. Remover e POST (com rate limit)
                current_bans.discard(gamertag)
                new_value = "\r\n".join(sorted(current_bans))

                post_data = {
                    "category": "general",
                    "key": "bans",
                    "value": new_value,
                }

                await _rate_limited_delay()
                async with session.post(
                    base_url, headers=headers, json=post_data,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("status") == "success":
                            print(f"[UNBAN] [V] Settings API: {gamertag} DESBLOQUEADO")
                            return True
                        else:
                            print(f"[UNBAN] [X] Settings API POST resposta: {result}")
                    else:
                        print(f"[UNBAN] [X] Settings API POST HTTP {resp.status}")

        except Exception as e:
            print(f"[UNBAN] [X] Settings API erro: {e}")

    return False


# ==================== BAN IMEDIATO (FUNÇÃO PRINCIPAL) ====================


async def ban_player_immediate_async(gamertag, xuid, reason, infraction_type, evidence=None):
    """
    Banimento IMEDIATO — 3 camadas paralelas + restart inteligente.

    Execução paralela via asyncio.gather():
      1. FTP ban.txt (XUID — persistente, DayZ server level)
      2. Settings API (Gamertag — bloqueio IMEDIATO, proxy Nitrado)
      3. Kick API (tentativa, geralmente HTTP 500 em DayZ Xbox — silenciado)

    Pós-execução:
      4. Restart inteligente (acumulação 2min + cooldown 15min) para releitura ban.txt
      5. Notificação Discord com status de cada operação
      6. Registro no Muro da Vergonha
    """

    # 0. Tentar recuperar XUID se vier None
    if not xuid:
        xuid = database.get_player_id(gamertag)
        if xuid:
            print(f"[AUTO-BAN] ID recuperado do banco para {gamertag}: {xuid}")

    # [DEDUP] Verificar se jogador já foi banido nesta sessão
    dedup_key = xuid if xuid else gamertag.lower()
    if dedup_key in _banned_this_session:
        print(
            f"[AUTO-BAN] [SKIP] {gamertag} já banido nesta sessão — "
            f"ignorando duplicata ({infraction_type})"
        )
        return True  # Já banido, considera sucesso

    print(f"\n{'=' * 60}")
    print(f"[AUTO-BAN] BANIMENTO IMEDIATO (Settings API + FTP + Restart)")
    print(f"Jogador: {gamertag}")
    print(f"ID/XUID: {xuid or 'N/A'}")
    print(f"Motivo: {reason}")
    print(f"Tipo: {infraction_type}")
    print(f"{'=' * 60}\n")

    # [SEC] PROTEÇÃO: Verificar se é admin protegido
    if xuid and xuid in PROTECTED_XUIDS:
        print(f"\n{'=' * 60}")
        print(f"[!] [PROTEÇÃO] ADMIN DETECTADO - BAN BLOQUEADO!")
        print(f"Jogador: {gamertag}")
        print(f"XUID: {xuid}")
        print(f"Infração detectada: {infraction_type}")
        print(f"Motivo: {reason}")
        print(f"{'=' * 60}\n")

        # Registrar infração para auditoria (sem banir)
        record_infraction(
            gamertag=gamertag,
            infraction_type=f"{infraction_type}_ADMIN_PROTECTED",
            description=f"[ADMIN PROTEGIDO] {reason}",
            evidence=evidence,
            xuid=xuid,
        )

        print(
            f"[AUTO-BAN] Infracao registrada para auditoria, mas admin NAO foi banido"
        )
        return False  # Não banir

    # 1. Registrar infração NO BANCO PRIMEIRO (fonte da verdade)
    infraction_id = record_infraction(
        gamertag=gamertag,
        infraction_type=infraction_type,
        description=reason,
        evidence=evidence,
        xuid=xuid,
    )

    # 2. Marcar identidade no banco local
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE player_identities
            SET last_seen = CURRENT_TIMESTAMP
            WHERE gamertag = ? OR xuid = ?
        """,
            (gamertag, xuid),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUTO-BAN] [X] Erro ao marcar identidade: {e}")

    # 3. EXECUÇÃO PARALELA: FTP ban.txt + Settings API + Kick API
    results = await asyncio.gather(
        asyncio.to_thread(add_to_nitrado_banlist, gamertag, xuid, reason),  # FTP (XUID)
        ban_player_settings_api(gamertag),                                   # Settings API (IMEDIATO)
        kick_player_api(gamertag, reason),                                   # Kick API (silenciado)
        return_exceptions=True,
    )

    ok_ftp = results[0] is True
    ok_settings = results[1] is True
    ok_kick = results[2] is True

    print(
        f"[AUTO-BAN] Resultado: "
        f"FTP={'OK' if ok_ftp else 'FAIL'} | "
        f"SETTINGS={'OK' if ok_settings else 'FAIL'} | "
        f"KICK={'OK' if ok_kick else 'N/A'}"
    )

    # 4. Restart SOMENTE se Settings API falhou e FTP é o único método
    # Se Settings API funcionou → jogador já está bloqueado, restart desnecessário.
    # Se Settings API falhou e FTP funcionou → restart é necessário para o DayZ ler ban.txt.
    if ok_ftp and not ok_settings:
        print(f"[AUTO-BAN] Settings API falhou — agendando restart para aplicar ban.txt")
        await schedule_restart_for_ban(gamertag)

    # 5. Enviar notificação Discord (com status de cada operação)
    send_ban_notification_discord(
        gamertag, xuid, reason, infraction_type, evidence, infraction_id,
        kick_status=ok_kick, ftp_status=ok_ftp, settings_api_status=ok_settings,
    )

    # 6. Adicionar ao Muro da Vergonha
    add_to_hall_of_shame(gamertag, xuid, reason, infraction_type, infraction_id)

    # [DEDUP] Marcar como banido nesta sessão para evitar duplicatas futuras
    _banned_this_session.add(dedup_key)

    overall_success = ok_ftp or ok_settings  # Pelo menos um método deve ter sucesso
    if overall_success:
        if ok_settings:
            print(
                f"\n[AUTO-BAN] [OK] BANIMENTO COMPLETO: {gamertag} "
                f"(bloqueio IMEDIATO via proxy Nitrado)"
            )
        else:
            print(
                f"\n[AUTO-BAN] [OK] BANIMENTO VIA FTP: {gamertag} "
                f"(aguardando restart para aplicar)"
            )
    else:
        print(f"\n[AUTO-BAN] [AVISO] BANIMENTO PARCIAL: {gamertag}")

    # 7. BAN DE ALTS — Banir automaticamente contas vinculadas (Device ID / IP / XUID)
    if ok_settings:
        try:
            alts = database.find_alts(gamertag)
            if alts:
                alts_to_ban = [
                    alt for alt in alts
                    if not is_already_banned(alt)
                ]
                if alts_to_ban:
                    print(
                        f"[AUTO-BAN] [ALTS] {len(alts_to_ban)} alt(s) detectada(s) "
                        f"para {gamertag}: {', '.join(alts_to_ban)}"
                    )
                    for alt_gt in alts_to_ban:
                        alt_result = await ban_player_settings_api(alt_gt)
                        _banned_this_session.add(alt_gt.lower())
                        if alt_result:
                            print(f"[AUTO-BAN] [ALTS] [V] {alt_gt} BLOQUEADO (alt de {gamertag})")
                            record_infraction(
                                gamertag=alt_gt,
                                infraction_type=f"alt_of_{infraction_type}",
                                description=f"Alt de {gamertag} — banida automaticamente",
                                xuid=database.get_player_id(alt_gt),
                            )
                        else:
                            print(f"[AUTO-BAN] [ALTS] [X] {alt_gt} falhou")
                else:
                    print(f"[AUTO-BAN] [ALTS] Alts de {gamertag} já banidas nesta sessão")
        except Exception as e:
            print(f"[AUTO-BAN] [ALTS] Erro ao banir alts: {e}")

    return overall_success


def ban_player_immediate(gamertag, xuid, reason, infraction_type, evidence=None):
    """
    Wrapper síncrono para ban_player_immediate_async.
    Usado por scripts standalone (execute_ban.py) que não rodam em contexto async.
    Para chamadas de contexto async, use: await ban_player_immediate_async(...)
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Já em contexto async — agendar como task (fire-and-forget)
        import warnings
        warnings.warn(
            "ban_player_immediate() chamado de contexto async. "
            "Use 'await ban_player_immediate_async()' em vez disso.",
            stacklevel=2,
        )
        asyncio.ensure_future(
            ban_player_immediate_async(gamertag, xuid, reason, infraction_type, evidence)
        )
        return True  # Best-effort
    else:
        # Sem event loop — rodar sincronamente
        return asyncio.run(
            ban_player_immediate_async(gamertag, xuid, reason, infraction_type, evidence)
        )


# ==================== APIs NITRADO (SILENCIADAS — 501/500 em DayZ Xbox) ====================
# Estas APIs NÃO funcionam para DayZ Xbox (has_playermanagement_feature: False)
# Mantidas como fallback caso a Nitrado implemente no futuro.
# Logs reduzidos — sem spam de erros no journal.


async def ban_player_api(identifier):
    """
    Bane jogador via API Nitrado (/games/banlist).
    NOTA: Retorna HTTP 501 (Not Implemented) para DayZ Xbox.
    Mantida como fallback — usar ban_player_settings_api() como método principal.
    """
    nitrado_token = os.getenv("NITRADO_TOKEN")
    service_id = os.getenv("SERVICE_ID")

    if not nitrado_token or not service_id:
        return False

    url = f"https://api.nitrado.net/services/{service_id}/gameservers/games/banlist"
    headers = {
        "Authorization": f"Bearer {nitrado_token}",
        "Content-Type": "application/json",
    }
    payload = {"identifier": identifier}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        print(f"[AUTO-BAN] [V] Ban API: {identifier} bloqueado")
                        return True
                # Silenciado: HTTP 501 é esperado para DayZ Xbox
    except Exception:
        pass
    return False


async def kick_player_api(identifier, reason="Infração Detectada"):
    """
    Expulsa jogador via API dedicada (/games/players/kick).
    NOTA: Retorna HTTP 500 para DayZ Xbox.
    Mantida como tentativa — Settings API já bloqueia no proxy.
    """
    nitrado_token = os.getenv("NITRADO_TOKEN")
    service_id = os.getenv("SERVICE_ID")

    if not nitrado_token or not service_id:
        return False

    url = f"https://api.nitrado.net/services/{service_id}/gameservers/games/players/kick"
    headers = {
        "Authorization": f"Bearer {nitrado_token}",
        "Content-Type": "application/json",
    }
    payload = {"identifier": identifier}
    if reason:
        payload["reason"] = reason

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        print(f"[AUTO-BAN] [V] Kick API: {identifier} expulso")
                        return True
                # Silenciado: HTTP 500 é esperado para DayZ Xbox
    except Exception:
        pass
    return False


# ==================== FTP BAN.TXT (PERSISTENTE) ====================


def add_to_nitrado_banlist(gamertag, xuid, reason):
    """Adiciona jogador ao ban.txt do servidor Nitrado via FTP"""

    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")
    ftp_port = int(os.getenv("FTP_PORT", 21))

    if not all([ftp_host, ftp_user, ftp_pass]):
        print(f"[AUTO-BAN] [X] Credenciais FTP não configuradas")
        return False

    try:
        # Conectar ao FTP
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=30)
        ftp.login(ftp_user, ftp_pass)

        # Caminho do arquivo de banimentos
        ban_file_path = "/dayzxb/config/ban.txt"

        # Baixar ban.txt atual
        ban_list = []
        try:
            bio = BytesIO()
            ftp.retrbinary(f"RETR {ban_file_path}", bio.write)
            bio.seek(0)
            ban_list = bio.read().decode("utf-8", errors="ignore").splitlines()
        except Exception:
            print(f"[AUTO-BAN] Arquivo ban.txt não existe, será criado")

        # Usar XUID se disponível, senão gamertag
        ban_id = xuid if xuid else gamertag

        # Verificar se já está banido
        for line in ban_list:
            if ban_id.lower() in line.lower():
                print(
                    f"[AUTO-BAN] [OK] {gamertag} ({ban_id}) já está banido no Nitrado"
                )
                ftp.quit()
                return True

        # Adicionar novo ban
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if xuid:
            new_ban_line = f"{xuid}  // {gamertag} - {reason} - {timestamp} [AUTO-BAN]"
        else:
            new_ban_line = f"{gamertag}  // {reason} - {timestamp} [AUTO-BAN]"

        ban_list.append(new_ban_line)

        # Upload novo ban.txt
        bio = BytesIO("\n".join(ban_list).encode("utf-8"))
        bio.seek(0)
        ftp.storbinary(f"STOR {ban_file_path}", bio)

        ftp.quit()

        print(f"[AUTO-BAN] [OK] Adicionado ao ban.txt do Nitrado")
        return True

    except Exception as e:
        print(f"[AUTO-BAN] [X] Erro ao adicionar ao Nitrado: {e}")
        return False


# ==================== NOTIFICAÇÃO DISCORD ====================


def send_ban_notification_discord(
    gamertag, xuid, reason, infraction_type, evidence, infraction_id,
    kick_status=None, ftp_status=None, settings_api_status=None,
):
    """Envia notificação de banimento para Discord (com status de operações)"""

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    # AltDetector: Busca contas secundárias vinculadas
    try:
        import database

        identity = database.get_player_identity(gamertag)
        alts = database.find_alts(gamertag)
        alts_str = (
            ", ".join([f"`{a}`" for a in alts])
            if alts
            else "Nenhuma conta secundária detectada."
        )
        device_id = identity["device_id"] if identity else None
    except Exception:
        alts_str = "Erro ao cruzar dados de Alts."
        device_id = None

    if not webhook_url:
        print(f"[AUTO-BAN] [!] Webhook Discord não configurado")
        return False

    # Determinar cor baseado na severidade
    severity = "CRÍTICA"
    for sev, types in InfractionType.CATEGORIES.items():
        if infraction_type in types:
            severity = sev
            break

    color = 0xFF0000 if severity == "CRÍTICA" else 0xFF6600  # Vermelho ou Laranja

    # Criar embed
    embed = {
        "title": "🔨 [BAN] BANIMENTO AUTOMÁTICO",
        "description": f"**{gamertag}** foi banido automaticamente do servidor!",
        "color": color,
        "fields": [
            {"name": "👤 Jogador", "value": f"**{gamertag}**", "inline": True},
            {"name": "🆔 XUID", "value": xuid or "N/A", "inline": True},
            {"name": "📱 Device ID", "value": device_id or "N/A", "inline": True},
            {"name": "⚠️ Severidade", "value": f"**{severity}**", "inline": True},
            {"name": "🚨 Infração", "value": f"`{infraction_type}`", "inline": False},
            {"name": "📋 Motivo", "value": reason, "inline": False},
            {
                "name": "🔗 Contas Vinculadas (Alts)",
                "value": alts_str,
                "inline": False,
            },
        ],
        "footer": {
            "text": f"ID: {infraction_id} | Anti-Cheat BigodeTexas v2 (Settings API)"
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Adicionar evidências se disponível
    if evidence:
        embed["fields"].append(
            {
                "name": "🔍 Evidência",
                "value": f"```{evidence[:200]}```",
                "inline": False,
            }
        )

    # Status das operações (3 camadas + restart)
    if settings_api_status is not None:
        status_lines = [
            f"Settings API: {'✅ BLOQUEADO (imediato)' if settings_api_status else '❌ FALHOU'}",
            f"FTP ban.txt: {'✅ OK (persistente)' if ftp_status else '❌ FALHOU'}",
        ]
        if ftp_status and not settings_api_status:
            status_lines.append("🔄 Restart agendado (Settings API falhou, restart aplica ban.txt)")
        elif kick_status:
            status_lines.append("Kick API: ✅ Expulso")

        embed["fields"].append(
            {
                "name": "⚙️ Status das Operações",
                "value": "\n".join(status_lines),
                "inline": False,
            }
        )

    payload = {
        "username": "Sistema Anti-Cheat",
        "avatar_url": "https://i.imgur.com/S71j4qO.png",
        "embeds": [embed],
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            print(f"[AUTO-BAN] [V] Notificação enviada ao Discord")
            return True
        else:
            print(f"[AUTO-BAN] [X] Erro ao enviar Discord: {response.status_code}")
            return False
    except Exception as e:
        print(f"[AUTO-BAN] [X] Erro ao enviar Discord: {e}")
        return False


# ==================== MURO DA VERGONHA ====================


def add_to_hall_of_shame(gamertag, xuid, reason, infraction_type, infraction_id):
    """Adiciona ao Muro da Vergonha (tabela já registrada em infractions)"""

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # Buscar Discord ID via discord_links_247 (gamertag -> discord_id)
        discord_id = None
        cur.execute(
            "SELECT discord_id FROM discord_links_247 WHERE gamertag = ?",
            (gamertag,),
        )
        row = cur.fetchone()
        discord_id = row[0] if row else None

        if discord_id:
            cur.execute(
                "UPDATE infractions SET discord_id = ? WHERE id = ?",
                (discord_id, infraction_id),
            )
            conn.commit()

        print("[AUTO-BAN] [V] Adicionado ao Muro da Vergonha")
        return True

    except Exception as e:
        print(f"[AUTO-BAN] [X] Erro ao adicionar ao Muro: {e}")
        return False
    finally:
        conn.close()


def get_hall_of_shame(limit=50):
    """Retorna lista do Muro da Vergonha para exibição no site"""

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                gamertag,
                xuid,
                infraction_type,
                severity,
                description,
                detected_at,
                evidence
            FROM infractions
            WHERE auto_banned = 1 AND ban_lifted = 0
            ORDER BY detected_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = []
        for row in cur.fetchall():
            results.append(
                {
                    "gamertag": row[0],
                    "xuid": row[1],
                    "infraction_type": row[2],
                    "severity": row[3],
                    "description": row[4],
                    "detected_at": row[5],
                    "evidence": row[6],
                }
            )

        return results

    except Exception as e:
        print(f"[AUTO-BAN] Erro ao buscar Muro da Vergonha: {e}")
        return []
    finally:
        conn.close()


# ==================== FUNÇÕES DE DETECÇÃO ====================


def detect_lag_machine(player_name, item_count_per_minute):
    """Detecta Lag Machine (spam de construção)"""
    if item_count_per_minute > 10:
        return True, f"Spam de construção: {item_count_per_minute} itens/min"
    return False, None


def detect_fly_hack(player_name, height, location):
    """Detecta Fly Hack (construção em altura ilegal)"""
    max_height = 120  # Padrão para cidades

    if height > 1000:
        return True, f"Sky Base: Construção a {height}m de altura"
    elif height > max_height:
        return True, f"Fly Hack: Construção a {height}m (máx: {max_height}m)"

    return False, None


def detect_underground_base(player_name, height):
    """Detecta Underground Base"""
    if height < -10:
        return True, f"Underground Base: Construção a {height}m abaixo do solo"
    return False, None


def detect_banned_item(player_name, item_name):
    """Detecta uso de itens banidos"""
    banned_items = ["TireRepairKit", "Shelter"]

    if any(banned in item_name for banned in banned_items):
        return True, f"Item banido: {item_name}"
    return False, None


# Inicializar tabela ao importar
ensure_infractions_table()


if __name__ == "__main__":
    print("Sistema de Banimento Automático - BigodeTexas")
    print("Versão: 2.0 (Settings API + FTP + Restart Inteligente)")
    print("\nTipos de Infrações Detectadas:\n")

    for severity, types in InfractionType.CATEGORIES.items():
        print(f"\n{severity}:")
        for t in types:
            print(f"  - {t}")

    print("\nFunções disponíveis:")
    print("  ban_player_settings_api(gamertag)    — Bloqueio IMEDIATO via proxy Nitrado")
    print("  unban_player_settings_api(gamertag)  — Remove bloqueio do proxy")
    print("  ban_player_immediate_async(...)      — Ban completo (FTP + Settings + Restart)")
    print("  set_callbacks(restart_fn, notify_fn) — Registra callbacks do main_247.py")
