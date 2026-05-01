# -*- coding: utf-8 -*-
"""
main_247.py - DEFINITIVE 24/7 Security Bot (Consolidated)
=========================================================
Merged from 8 versions into one clean, production-ready bot.
Features: Base sovereignty, raid scheduler, truck monitoring,
          clan portal, glitch detection, alt detection.

Author: BigodeTexas / Bot 24/7 Security System
"""

import asyncio
import io
import json
import logging
import math
import os
import re
from datetime import datetime, timedelta, timezone

import discord
import discord.ui as ui
import requests
from discord.ext import commands, tasks
from dotenv import load_dotenv

import database
import glitch_detector
from auto_ban_system import ban_player_immediate_async, ban_player_immediate, is_already_banned, ban_player_settings_api, unban_player_settings_api
from ftp_helpers import connect_ftp, download_file, upload_file
import admin_dashboard

# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bot247")

# =============================================================================
# CONFIGURATION (from .env)
# =============================================================================
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("FATAL: DISCORD_TOKEN not set in .env file")
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")
try:
    BAN_CHANNEL_ID = int(os.getenv("BAN_CHANNEL", 0)) or None
except ValueError:
    BAN_CHANNEL_ID = None
    logger.error("BAN_CHANNEL must be a numeric channel ID")
VERIFIED_ROLE_ID = os.getenv("VERIFIED_ROLE_ID")
PORTAL_CHANNEL_ID = os.getenv("PORTAL_CHANNEL_ID")

# Runtime flag: False se bot não tem MANAGE_ROLES (verificado no on_ready)
_can_assign_roles = True
RADAR_WEBHOOK_URL = os.getenv("RADAR_WEBHOOK_URL")
RULES_CHANNEL_ID = os.getenv("RULES_CHANNEL_ID", "1384330092586729472")
TRUCK_ALERTS_CHANNEL_ID = os.getenv("TRUCK_ALERTS_CHANNEL_ID", "1384330076174155867")
ADMIN_BACKUP_CHANNEL_ID = os.getenv("ADMIN_BACKUP_CHANNEL_ID")  # Canal admin para receber backup do DB

# Nitrado FTP paths (configurable via .env with defaults)
GAMEPLAY_CONFIG_PATH = os.getenv(
    "GAMEPLAY_CONFIG_PATH",
    "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json",
)
LOCAL_GAMEPLAY_CONFIG = os.getenv("LOCAL_GAMEPLAY_CONFIG", "cfggameplay_temp.json")

# =============================================================================
# GLOBAL STATE
# =============================================================================
_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bot_log_state.json"
)


def _load_log_state():
    """Carrega offset e arquivo de log salvos em disco (persiste entre restarts)."""
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("log_file"), data.get("offset", 0)
    except Exception:
        pass
    return None, 0


def _save_log_state(log_file, offset):
    """Salva offset e arquivo de log em disco de forma segura contra corrompimento (tmp -> rename)"""
    temp_file = _STATE_FILE + ".tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump({"log_file": log_file, "offset": offset}, f)
        os.replace(temp_file, _STATE_FILE)
    except Exception as e:
        logger.warning(f"[STATE] Falha ao salvar estado do log: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


current_log_file, last_byte_offset = _load_log_state()
_player_id_cache = {}
_recent_player_positions = {}  # {gamertag: {"x": float, "z": float, "t": float}}
_fireplace_spam_tracker = {}  # {gamertag: [timestamp1, timestamp2, ...]}

# Truck monitoring state
active_truck_timers = {}  # {(x,z): {"expiry": datetime, "player": str, "warning_sent": bool}}
last_available_trucks = set()

# FTP health monitoring state
_ftp_fail_count = 0
_ftp_health_alert_sent = False

# Ban notification rate-limiting queue (max 1 msg/second to avoid Discord rate-limit)
_ban_notify_queue: asyncio.Queue = asyncio.Queue()

# === MODO PAUSA ===
# Bot inicia PAUSADO: conectado ao Discord mas sem ler FTP/Nitrado.
# Apenas o raid_scheduler e drain_ban_queue rodam sempre.
# No sabado 20h-22h BRT, o raid_scheduler ativa as tasks FTP.
_bot_paused = True

# Dynamic server config (overridable via !config command, persistent in DB)
_server_config = {
    "raid_start_hour": 20,   # BRT
    "raid_end_hour": 22,     # BRT
    "fire_limit": 2,         # max fogueiras por jogador fora da base
    "base_radius": int(os.getenv("BASE_RADIUS", 50)),  # metros de soberania
}

# Official Truck Kit spawn coordinates (from cfgeventspawns.xml)
TRUCK_SPAWNS = [
    (2906, 9736),
    (1577, 10434),
    (4986, 12949),
    (5960, 10146),
    (8667, 13278),
    (5664, 13129),
    (4832, 10236),
    (5276, 10581),
    (1045, 9971),
    (5227, 11521),
    (3789, 13001),
    (1798, 9127),
    (2009, 10077),
    (7735, 14834),
    (8857, 11649),
    (4131, 13122),
    (2276, 15255),
    (1522, 14049),
    (3251, 13731),
    (5770, 15185),
    (4406, 13568),
    (7748, 5119),
    (3575, 6990),
    (7791, 6910),
    (7076, 2689),
    (3633, 3692),
    (4429, 8215),
    (2220, 5200),
    (560, 5410),
    (4637, 9505),
    (8405, 6596),
    (6944, 7693),
    (1364, 4114),
    (8409, 4441),
    (2206, 3372),
    (3012, 6762),
    (2041, 12167),
    (7299, 3309),
    (10554, 14322),
    (6265, 3786),
    (10362, 7419),
    (9004, 5989),
    (2733, 5996),
    (5339, 8617),
    (5678, 2970),
    (10224, 1893),
    (13058, 7050),
    (11327, 12564),
    (7414, 2902),
    (9372, 2017),
    (12373, 14194),
    (12766, 9737),
    (12291, 9180),
    (9914, 6694),
    (9851, 8710),
    (11758, 6440),
    (12659, 8792),
    (7043, 2621),
    (12046, 5117),
    (10289, 14176),
    (2253, 10861),
    (4193, 8920),
    (6324, 7708),
    (5281, 5511),
    (8214, 9051),
    (981, 7679),
    (9186, 8092),
    (4045, 11620),
    (4957, 13034),
    (7711, 3541),
    (5258, 9789),
    (4812, 10559),
    (5081, 12738),
    (289, 6591),
    (2311, 5205),
    (3040, 12342),
    (3115, 9212),
    (1927, 8118),
    (11119, 11950),
    (12252, 10592),
    (10268, 9484),
    (9788, 12659),
    (3588, 2191),
    (12739, 15065),
    (4962, 2423),
    (9684, 8900),
    (11443, 7523),
    (8076, 3367),
    (12658, 14744),
    (13471, 13067),
    (11714, 14243),
    (12304, 14322),
    (11951, 12505),
    (11617, 7294),
    (9901, 5467),
    (10257, 3617),
]

# =============================================================================
# BOT SETUP
# =============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


# =============================================================================
# HELPERS - Item Classification
# =============================================================================


def _is_garden(item_name, class_name=""):
    """Check if item is a garden/planting type. Checks BOTH friendly name and class name."""
    garden_keywords = [
        "gardenplot",
        "garden_plot",
        "greenhouse",
        "planting",
        "plot",
        "farming",
    ]
    # DayZ class names that ARE gardens (even if log says "Nameless Object")
    garden_classes = ["gardenplot", "gardensmall", "gardenlarge"]
    name_lower = item_name.lower()
    class_lower = class_name.lower() if class_name else ""
    # Check friendly name
    if any(kw in name_lower for kw in garden_keywords):
        return True
    # Check class name (catches "Nameless Object <GardenPlot>" cases)
    if class_lower and any(
        gc in class_lower for gc in garden_classes + garden_keywords
    ):
        return True
    return False


def _is_fireplace(item_name, class_name=""):
    """Check if item is a fireplace/fire type. Checks BOTH friendly name and class name."""
    keywords = ["fireplace", "oven", "stove", "campfire", "fire"]
    for name in [item_name, class_name]:
        if not name:
            continue
        name_lower = name.lower()
        if "barrel" in name_lower and "hole" in name_lower:
            return True
        if any(kw in name_lower for kw in keywords):
            return True
    return False


def _is_garden_or_fireplace(item_name, class_name=""):
    return _is_garden(item_name, class_name) or _is_fireplace(item_name, class_name)


def _check_clan_permission(player_name, base):
    """Check if player is a clan member of the base owner. Returns True if allowed."""
    dono_discord = base.get("owner_discord_id")
    if dono_discord:
        clan_id = database.get_clan_id_by_member(dono_discord)
        if clan_id:
            members = database.get_clan_members_gamertags(clan_id)
            if player_name in members:
                return True
    return False


# =============================================================================
# NOTIFICATION HELPERS
# =============================================================================


async def notify_ban(message):
    """Send ban/security notification via rate-limited queue (max 1/sec)."""
    await _ban_notify_queue.put(message)


async def _notify_ban_direct(message):
    """Internal: actually sends ban notification (called by drain_ban_queue)."""
    logger.info(f"[NOTIFY] {message}")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            await asyncio.to_thread(
                requests.post, webhook_url, json={"content": message}, timeout=10
            )
        except Exception as e:
            logger.warning(f"Webhook error: {e}")
    if BAN_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(BAN_CHANNEL_ID))
            if not channel:
                channel = await bot.fetch_channel(int(BAN_CHANNEL_ID))
            if channel:
                await channel.send(message)
        except Exception as e:
            logger.warning(f"Bot channel send error: {e}")


async def send_radar_alert(message, owner_discord_id):
    """Send radar alerts to webhook and DM to base owner."""
    logger.info(f"[RADAR] {message}")
    if RADAR_WEBHOOK_URL:
        payload = {"content": message}
        if owner_discord_id:
            payload["content"] = f"<@{owner_discord_id}>\n" + message
        try:
            await asyncio.to_thread(
                requests.post, RADAR_WEBHOOK_URL, json=payload, timeout=10
            )
        except Exception:
            pass
    if owner_discord_id:
        try:
            user = await bot.fetch_user(int(owner_discord_id))
            if user:
                await user.send(
                    f"**ALERTA DE BASE**\n{message}\n\nEntre no servidor para defender seu patrimonio!"
                )
        except Exception as e:
            logger.warning(f"Radar DM error for {owner_discord_id}: {e}")


async def notify_admin_log(message):
    """Send audit log to admin channel and webhook."""
    logger.info(f"[ADMIN] {message}")
    if BAN_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(BAN_CHANNEL_ID))
            if channel:
                await channel.send(message)
        except Exception:
            pass
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            await asyncio.to_thread(
                requests.post, webhook_url, json={"content": message}, timeout=10
            )
        except Exception:
            pass


async def notify_truck_alert(message):
    """Send truck alerts to the dedicated truck channel."""
    logger.info(f"[TRUCK] {message}")
    if TRUCK_ALERTS_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(TRUCK_ALERTS_CHANNEL_ID))
            if not channel:
                channel = await bot.fetch_channel(int(TRUCK_ALERTS_CHANNEL_ID))
            if channel:
                await channel.send(message)
        except Exception as e:
            logger.warning(f"Truck alert send error: {e}")


# =============================================================================
# NITRADO HELPERS
# =============================================================================


async def restart_nitrado():
    """Call Nitrado API to restart the game server."""
    if not NITRADO_TOKEN or not SERVICE_ID:
        logger.error("Nitrado credentials missing in .env")
        return False
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
    try:
        response = await asyncio.to_thread(
            requests.post, url, headers=headers, timeout=10
        )
        if response.status_code == 200:
            logger.info("Nitrado restart command sent successfully")
            return True
        else:
            logger.error(
                f"Nitrado restart error: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Nitrado connection error: {e}")
        return False


async def enforce_free_building():
    """Ensure building restrictions are ACTIVE (construção restringida) in cfggameplay.json."""
    logger.info("Checking building restriction configuration...")
    downloaded = await asyncio.to_thread(
        download_file, GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG
    )
    if not downloaded:
        logger.warning("Could not download cfggameplay.json for building check")
        return
    try:
        if not os.path.exists(LOCAL_GAMEPLAY_CONFIG):
            logger.warning(
                f"File {LOCAL_GAMEPLAY_CONFIG} nulo ou não criado pós-download."
            )
            return
        with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
            config = json.load(f)
        modified = False
        if "BaseBuildingData" not in config:
            config["BaseBuildingData"] = {}
        if "HologramData" not in config["BaseBuildingData"]:
            config["BaseBuildingData"]["HologramData"] = {}
        hologram_data = config["BaseBuildingData"]["HologramData"]
        keys_to_restrict = [
            "disableIsCollidingBBoxCheck",
            "disableIsCollidingPlayerCheck",
            "disableIsClippingRoofCheck",
            "disableIsBaseViableCheck",
            "disableIsCollidingGPlotCheck",
            "disableIsCollidingAngleCheck",
            "disableIsPlacementPermittedCheck",
            "disableHeightPlacementCheck",
            "disableIsUnderwaterCheck",
            "disableIsInTerrainCheck",
            "disableColdAreaBuildingCheck",
        ]
        for key in keys_to_restrict:
            if hologram_data.get(key) is not True:
                hologram_data[key] = True
                modified = True
        if modified:
            logger.warning(
                "[BUILD] Construcao restringida detectada — liberando construcao livre..."
            )
            with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
                json.dump(config, f, indent=4)
            uploaded = await asyncio.to_thread(
                upload_file, LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH
            )
            if uploaded:
                await notify_ban(
                    "**CONSTRUCAO LIVRE RESTAURADA**\nO bot detectou construcao restringida e liberou a construcao livre no cfggameplay.json."
                )
        else:
            logger.info("[BUILD] Construcao livre ativa. OK.")
    except Exception as e:
        logger.error(f"Error processing gameplay JSON: {e}")
    finally:
        if os.path.exists(LOCAL_GAMEPLAY_CONFIG):
            os.remove(LOCAL_GAMEPLAY_CONFIG)


# =============================================================================
# LOG PARSER - Core Security Logic
# =============================================================================


async def parse_log_line(line):
    """Process a single log line and apply all security rules."""
    line = line.strip()
    if not line:
        return

    # Passa a linha para o detector de glitches de emote, relog veloz e boosters
    await glitch_detector.process_line(line)

    # --- 0. CONNECTION DETECTION (Identity Sync / Alt Detector) ---
    if "connected" in line.lower() and "player" in line.lower():
        if "has been disconnected" in line.lower():
            # Captura posição de Logout
            pattern_logout = r'Player "(?P<name>[^"]+)"\(id=[^ ]+ pos=<(?P<coords>[^>]+)>\) has been disconnected'
            match_logout = re.search(pattern_logout, line)
            if match_logout:
                p_name = match_logout.group("name")
                coords_str = match_logout.group("coords")
                try:
                    parts = coords_str.split(",")
                    lx, lz = float(parts[0]), float(parts[1])
                    database.log_player_logout(p_name, lx, lz)
                    logger.info(f"Logout logado: {p_name} em [{int(lx)}, {int(lz)}]")
                except Exception:
                    pass
            return

        pattern_login = r'Player "(?P<name>[^"]+)"\(id=(?P<xuid>[^ )]+).+connected( from (?P<ip>[\d\.]+):)?'
        match_login = re.search(pattern_login, line)
        if match_login:
            p_name = match_login.group("name")
            p_xuid = match_login.group("xuid")
            p_ip = match_login.group("ip")
            _player_id_cache[p_name] = p_xuid
            database.log_connection(p_name, p_ip, p_xuid)
            logger.info(f"Identity synced: {p_name} ({p_xuid}) | IP: {p_ip or 'N/A'}")

            # --- ALT DETECTOR CHECK ---
            # Se o jogador logar em até 120s onde outro deslogou
            login_coords_pattern = r'Player ".+".+pos=<(?P<coords>[^>]+)>'
            match_pos = re.search(login_coords_pattern, line)
            if match_pos:
                try:
                    cparts = match_pos.group("coords").split(",")
                    cx, cz = float(cparts[0]), float(cparts[1])
                    possible_main = database.check_proximity_alt(p_name, cx, cz)
                    if possible_main:
                        await notify_admin_log(
                            f"**🌗 ALERTA DE CONTA SECUNDÁRIA (ALT) 🌗**\n"
                            f"O jogador **{p_name}** logou exatamente onde **{possible_main}** deslogou recentemente!\n"
                            f"Local: `[{int(cx)}, {int(cz)}]`"
                        )
                except Exception:
                    pass
            return

    # --- 0.1 KILL DETECTION (Killfeed) ---
    if (
        "killed" in line.lower()
        and "player" in line.lower()
        and " with " in line.lower()
    ):
        kill_pattern = (
            r'Player "(?P<killer>[^"]+)" \(id=[^ ]+ pos=<(?P<k_pos>[^>]+)>\) '
            r'killed Player "(?P<victim>[^"]+)" \(id=[^ ]+ pos=<(?P<v_pos>[^>]+)>\) '
            r"with (?P<weapon>[^ ]+) from (?P<dist>[\d\.]+)m"
        )
        match_kill = re.search(kill_pattern, line)
        if match_kill:
            logger.info(
                f"[KILL] {match_kill.group('killer')} killed {match_kill.group('victim')} "
                f"({match_kill.group('weapon')} - {match_kill.group('dist')}m)"
            )
            return

    # --- Main regex: extract player, coords, action ---
    pattern = r'Player "(?P<name>[^"]+)" \(id=(?P<xuid>[^ )]+) pos=<(?P<coords>[^>]+)>\)(?P<action_line>.+)'
    match = re.search(pattern, line)
    if not match:
        pattern_alt = r'Player "(?P<name>[^"]+)" .*(?:at|pos)=<(?P<coords>[^>]+)>.*'
        match = re.search(pattern_alt, line)
        if not match:
            return

    player_name = match.group("name")
    coords_str = match.group("coords")
    action_line = (
        match.group("action_line") if "action_line" in match.groupdict() else line
    )

    # Cache XUID if present
    if "xuid" in match.groupdict() and match.group("xuid"):
        p_xuid = match.group("xuid")
        _player_id_cache[player_name] = p_xuid
        database.update_player_identity(player_name, p_xuid)

    try:
        # DayZ ADM format: <X, Z_map, Y_height> - use X and Z_map for horizontal position
        parts = coords_str.split(",")
        x, z = float(parts[0]), float(parts[1])
        _recent_player_positions[player_name] = {
            "x": x,
            "z": z,
            "t": datetime.now(timezone.utc).timestamp(),
        }
    except Exception:
        return

    action_lower = action_line.lower()

    # --- 1. BUILD DETECTION ---
    if "built" in action_lower:

        # --- 1a. BUNKER MEDICAL ZONE (No-Build / Zero Tolerance) ---
        if math.hypot(x - 13280.0, z - 12100.0) <= 200:
            _xuid = _player_id_cache.get(player_name)
            if not is_already_banned(player_name, _xuid):
                await notify_ban(
                    f"**🚨 INVASÃO DE BUNKER (MÉDICO) 🚨**\n"
                    f"O jogador **{player_name}** tentou militarizar a zona de quarentena.\n"
                    f"Construção detectada nas coords: `[{int(x)}, {int(z)}]`\n"
                    f"O sistema baniu automaticamente."
                )
                await ban_player_immediate_async(
                    player_name,
                    _xuid,
                    f"Construção ilegal na área restrita do Bunker (13280, 12100)",
                    "bunker_invasion",
                )
            return

        base = database.get_base_at(x, z)
        if not base:
            if any(k in action_lower for k in ["fence", "gate", "watchtower"]):
                database.register_new_base(player_name, x, z)
                logger.info(f"Base registered: {player_name} at [{int(x)}, {int(z)}]")
                await notify_ban(
                    f"**SOBERANIA REGISTRADA**\n"
                    f"O jogador **{player_name}** construiu sua primeira estrutura "
                    f"em **[{int(x)}, {int(z)}]**.\nArea protegida em 50m!"
                )
        else:
            if base["owner"] != player_name:
                if _check_clan_permission(player_name, base):
                    return
                _xuid = _player_id_cache.get(player_name)
                if not is_already_banned(player_name, _xuid):
                    await notify_ban(
                        f"**BANIMENTO POR INVASAO**\n"
                        f"O jogador **{player_name}** tentou construir na base de **{base['owner']}**!"
                    )
                    await ban_player_immediate_async(
                        player_name,
                        _xuid,
                        f"Invasao de Base: Construindo em area de {base['owner']}",
                        "territory_invasion",
                    )

    # --- 2. PLACE DETECTION ---
    elif "placed" in action_lower:
        parts = re.split(r"placed\s+", action_line, flags=re.IGNORECASE)
        item_raw = parts[1].strip() if len(parts) > 1 else ""
        friendly_name = ""
        class_name = ""
        if "<" in item_raw:
            friendly_name = item_raw.split("<")[0].strip()
            class_name = item_raw.split("<")[1].split(">")[0].strip()
        else:
            friendly_name = item_raw if item_raw else "item"
        # Display name: prefer class_name when friendly is "Nameless Object"
        is_nameless = friendly_name.lower() == "nameless object"
        item_name = class_name if is_nameless and class_name else friendly_name

        base = database.get_base_at(x, z)

        # --- 2-SPAM. Fireplace Spam Filter (Toxic Griefing) ---
        if _is_fireplace(friendly_name, class_name):
            now_ts = datetime.now(timezone.utc).timestamp()
            history = _fireplace_spam_tracker.setdefault(player_name, [])
            history.append(now_ts)
            # Mantém apenas os últimos 5 minutos (300 segundos)
            history = [t for t in history if now_ts - t <= 300]
            _fireplace_spam_tracker[player_name] = history

            if len(history) >= 3:
                _xuid = _player_id_cache.get(player_name)
                if not is_already_banned(player_name, _xuid):
                    await notify_ban(
                        f"**🚨 BAN - SPAM DE FOGUEIRA (TOXIC GRIEFING) 🚨**\n"
                        f"O jogador **{player_name}** colocou 3 ou mais fogueiras em menos de 5 minutos!\n"
                        f"Provável tentativa de trancar portões da base alheia ou criar lag."
                    )
                    await ban_player_immediate_async(
                        player_name,
                        _xuid,
                        f"Griefing Toxico: Spam de fogueiras (3+ em 5 mins)",
                        "spam_exploit",
                    )
                return

        # --- 2-BARRICADA. Storage Barricading Exploit ---
        if any(
            kw in class_name.lower() or kw in friendly_name.lower()
            for kw in ["barrel", "woodencrate", "tent", "seachest"]
        ):
            if base and base["owner"] != player_name:
                if not _check_clan_permission(player_name, base):
                    _xuid = _player_id_cache.get(player_name)
                    if not is_already_banned(player_name, _xuid):
                        await notify_ban(
                            f"**🚨 BAN - BARRICADA DE INVASÃO 🚨**\n"
                            f"O invasor **{player_name}** tentou trancar a base de **{base['owner']}** usando {item_name} como bloqueio de porta!"
                        )
                        await ban_player_immediate_async(
                            player_name,
                            _xuid,
                            f"Barricada de Invasao: Usando {item_name} na porta da base de {base['owner']}",
                            "territory_invasion",
                        )
                    return

        # --- 2a-1. Anti-Torre de Invasão (Extended Radius / 80m) ---
        if (
            "watchtower" in class_name.lower()
            or "watchtower" in friendly_name.lower()
            or "torre" in friendly_name.lower()
        ):
            if not base:  # Fora dos 50m
                base_80m = database.get_base_at(x, z, radius=80)
                if base_80m and base_80m["owner"] != player_name:
                    if not _check_clan_permission(player_name, base_80m):
                        _xuid = _player_id_cache.get(player_name)
                        if not is_already_banned(player_name, _xuid):
                            await notify_ban(
                                f"**🚨 BAN - TORRE ILEGAL 🚨**\n"
                                f"O jogador **{player_name}** tentou construir uma torre muito proxima da base de **{base_80m['owner']}** para pular o muro!\n"
                            )
                            await ban_player_immediate_async(
                                player_name,
                                _xuid,
                                f"Torre Ilegal: Excedeu limite da base de {base_80m['owner']}",
                                "territory_invasion",
                            )
                        return

        # --- 2a. BUNKER MEDICAL ZONE (No-Build / Zero Tolerance) ---
        if math.hypot(x - 13280.0, z - 12100.0) <= 200:
            if any(
                k in class_name.lower() or k in friendly_name.lower()
                for k in ["kit", "tent", "watchtower", "fence", "gate"]
            ):
                _xuid = _player_id_cache.get(player_name)
                label = class_name if class_name else item_name
                if not is_already_banned(player_name, _xuid):
                    await notify_ban(
                        f"**🚨 INVASÃO DE BUNKER (MÉDICO) 🚨**\n"
                        f"O jogador **{player_name}** tentou militarizar a zona de quarentena.\n"
                        f"Objeto colocado: **{label}** nas coords `[{int(x)}, {int(z)}]`\n"
                        f"O sistema baniu automaticamente."
                    )
                    await ban_player_immediate_async(
                        player_name,
                        _xuid,
                        f"Acampamento ilegal na área restrita do Bunker (13280, 12100)",
                        "bunker_invasion",
                    )
                return
        # --- 2a. GARDEN DETECTION (Zero Tolerance) ---
        # GardenPlot = KICK IMEDIATO + BAN PERMANENTE em QUALQUER local, sem excecoes
        if _is_garden(friendly_name, class_name) or (is_nameless and not class_name):
            xuid = _player_id_cache.get(player_name)
            label = class_name if class_name else item_name
            local_info = (
                f" na base de **{base['owner']}**"
                if base
                else " **FORA DE BASE REGISTRADA**"
            )
            logger.warning(
                f"[GARDEN KICK+BAN] {player_name} placed {label} at [{int(x)},{int(z)}] "
                f"{'in base of ' + base['owner'] if base else 'outside any base'}"
            )
            if not is_already_banned(player_name, xuid):
                # ETAPA 1: Kick imediato via Settings API
                await ban_player_settings_api(player_name)
                kick_msg = (
                    "**KICK - GARDEN PROIBIDO**\n"
                    + f"Jogador: **{player_name}** foi expulso\!\n"
                    + f"Item: **{label}**{local_info}\nBan em 5s..."
                )
                await notify_ban(kick_msg)
                # ETAPA 2: Aguarda 5s
                await asyncio.sleep(5)
                # ETAPA 3: Ban permanente
                await unban_player_settings_api(player_name)
                await ban_player_immediate_async(
                    player_name,
                    xuid,
                    f"GardenPlot proibido{local_info.replace('**', '')}",
                    "garden_exploit",
                )
            return

        # --- 2b. Territory Invasion (non-garden items in someone's base) ---
        if base:
            if base["owner"] != player_name:
                if _check_clan_permission(player_name, base):
                    return
                _xuid = _player_id_cache.get(player_name)
                if not is_already_banned(player_name, _xuid):
                    await notify_ban(
                        f"**BANIMENTO POR INVASAO**\n"
                        f"O jogador **{player_name}** tentou colocar **{item_name}** "
                        f"na base de **{base['owner']}**!"
                    )
                    await ban_player_immediate_async(
                        player_name,
                        _xuid,
                        f"Invasao: Colocando {item_name} na area de {base['owner']}",
                        "territory_invasion",
                    )
        # --- 2c. Fireplace outside base (also banned) ---
        elif _is_fireplace(friendly_name, class_name):
            xuid = _player_id_cache.get(player_name)
            label = class_name if class_name else item_name
            if not is_already_banned(player_name, xuid):
                await notify_ban(
                    f"**BAN - FOGUEIRA FORA DE BASE**\n"
                    f"Jogador: **{player_name}**\n"
                    f"Item: **{label}** fora de base registrada\n"
                    f"Coordenadas: `[{int(x)}, {int(z)}]`"
                )
                await ban_player_immediate_async(
                    player_name,
                    xuid,
                    f"Fogueira proibida fora de base: {label}",
                    "fireplace_exploit",
                )

    # --- 3. DISMANTLE / DESTROY / RAID DETECTION ---
    elif "dismantled" in action_lower or "destroyed" in action_lower:
        split_keyword = "dismantled" if "dismantled" in action_lower else "destroyed"
        parts = re.split(
            r"{}\s+".format(split_keyword), action_line, flags=re.IGNORECASE
        )
        item_name = parts[1].split(" (")[0].strip() if len(parts) > 1 else "item"

        base = database.get_base_at(x, z)
        if base and base["owner"] != player_name:
            if _check_clan_permission(player_name, base):
                return
            guests = database.get_base_permissions(base["id"])
            if player_name in guests:
                return

            br_now = datetime.now(timezone.utc) - timedelta(hours=3)
            is_raid_hours = br_now.weekday() == 5 and 20 <= br_now.hour < 22

            if is_raid_hours:
                database.add_raid_incident(base["id"], player_name)
                recent_count = database.count_recent_incidents(base["id"])
                if recent_count >= 2:
                    msg = (
                        f"**RADAR DE BASE**: Raid em andamento na base de **{base['owner']}**!\n"
                        f"Invasor: `{player_name}`\nLocal: `{int(x)}, {int(z)}`"
                    )
                    await send_radar_alert(msg, base.get("owner_discord_id"))
            else:
                _xuid = _player_id_cache.get(player_name)
                if not is_already_banned(player_name, _xuid):
                    action_display = (
                        "Desmontando" if split_keyword == "dismantled" else "Destruindo"
                    )
                    await notify_ban(
                        f"**BANIMENTO POR RAID**\n"
                        f"O jogador **{player_name}** {'desmontou' if split_keyword == 'dismantled' else 'destruiu'} estruturas na base de "
                        f"**{base['owner']}** fora do horario!"
                    )
                    await ban_player_immediate_async(
                        player_name,
                        _xuid,
                        f"Raid em Base Protegida: {action_display} {item_name}",
                        "raid_exploit",
                    )

    # --- 4. CADEADO / GRIEFING COLETIVO (Rule 5) ---
    elif "attached" in action_lower and "combinationlock" in action_lower:
        base = database.get_base_at(x, z)
        if base and base["owner"] != player_name:
            if not _check_clan_permission(player_name, base):
                owner_name = base["owner"]
                t_now = datetime.now(timezone.utc).timestamp()
                accomplices = []

                for p_name, pos_data in list(_recent_player_positions.items()):
                    if t_now - pos_data["t"] > 600:
                        continue
                    if math.hypot(x - pos_data["x"], z - pos_data["z"]) <= 60:
                        if p_name != owner_name and not _check_clan_permission(
                            p_name, base
                        ):
                            accomplices.append(p_name)

                # Garante que o colocador do cadeado está na lista
                if player_name not in accomplices:
                    accomplices.append(player_name)

                for invader in accomplices:
                    invader_xuid = _player_id_cache.get(invader)
                    if not is_already_banned(invader, invader_xuid):
                        await notify_ban(
                            f"**🚨 BAN COLETIVO - SEQUESTRO DE BASE 🚨**\n"
                            f"O esquadrão de **{invader}** (Griefing de Cadeado) foi interceptado na base de **{owner_name}**!"
                        )
                        await ban_player_immediate_async(
                            invader,
                            invader_xuid,
                            f"Sequestro de Base: Esquadrão invasor na base de {owner_name}",
                            "territory_invasion",
                        )
                return

    # --- 5. TRUCK USAGE DETECTION ---
    elif "entered vehicle" in action_lower and "truck" in action_lower:
        match_x, match_z = int(x), int(z)
        for sx, sz in TRUCK_SPAWNS:
            if abs(match_x - sx) <= 15 and abs(match_z - sz) <= 15:
                coords_tuple = (match_x, match_z)
                if coords_tuple not in active_truck_timers:
                    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                    active_truck_timers[coords_tuple] = {
                        "expiry": expiry,
                        "player": player_name,
                        "warning_sent": False,
                    }
                    msg = (
                        f"**ALERTA DE CAMINHAO**\n"
                        f"O jogador **{player_name}** pegou um Caminhao de Kit!\n"
                        f"Local: `[{match_x}, {match_z}]`\n"
                        f"Tempo de vida: **60 minutos**"
                    )
                    await notify_truck_alert(msg)
                    logger.info(f"Truck timer started: {player_name} at {coords_tuple}")
                break


# =============================================================================
# FTP LOG MONITOR
# =============================================================================

# Conexão FTP persistente — evita reconectar a cada ciclo (economia de ~2.5s/ciclo)
_persistent_ftp = None


def _get_ftp_connection():
    """Retorna conexão FTP persistente. Reconecta automaticamente se morta."""
    global _persistent_ftp
    # Testar se conexão ainda está viva
    if _persistent_ftp is not None:
        try:
            _persistent_ftp.voidcmd("NOOP")
            return _persistent_ftp
        except Exception:
            logger.warning("[FTP] Conexão persistente caiu — reconectando...")
            _persistent_ftp = None

    # Reconectar
    ftp = connect_ftp()
    if ftp:
        logger.info("[FTP] Conexão persistente estabelecida.")
        _persistent_ftp = ftp
    else:
        logger.error("[FTP] Falha ao reconectar — log não monitorado neste ciclo.")
    return ftp


def _find_latest_adm_log(ftp):
    """Search FTP for the most recent .ADM log file."""
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            ftp.voidcmd("TYPE I")
            items = ftp.nlst()
            adm_files = []
            for f in items:
                # nlst() pode retornar caminho completo ou só o nome — normaliza
                basename = f.replace("\\", "/").split("/")[-1]
                if basename.lower().endswith(".adm"):
                    adm_files.append(f"{path}/{basename}")
            if adm_files:
                # Ordena por nome (contém datetime ISO) → último = mais recente
                return sorted(adm_files)[-1]
        except Exception:
            continue
    return None


def _ftp_fetch_new_lines(current_file, byte_offset):
    """Synchronous FTP operation: usa conexão persistente para ler novos bytes do log."""
    global _persistent_ftp
    ftp = _get_ftp_connection()
    if not ftp:
        return None, byte_offset, current_file
    try:
        latest = _find_latest_adm_log(ftp)
        if not latest:
            return None, byte_offset, current_file

        # Offset -1 = modo pausa -> pular para o fim do arquivo (ignorar historico)
        if byte_offset == -1:
            ftp.voidcmd("TYPE I")
            file_size = ftp.size(latest)
            logger.info(f"[PAUSE] Pulando para fim do log: {latest} (offset: {file_size})")
            return None, file_size, latest

        # Log file changed (server restart) - read from beginning
        if latest != current_file:
            ftp.voidcmd("TYPE I")
            file_size = ftp.size(latest)
            logger.info(
                f"New log detected: {latest} (size: {file_size}), reading from start"
            )
            if file_size > 0:
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {latest}", bio.write)
                new_content = bio.getvalue().decode("utf-8", errors="ignore")
                return new_content, file_size, latest
            return None, 0, latest

        ftp.voidcmd("TYPE I")
        server_size = ftp.size(current_file)

        # Log was reset/truncated
        if server_size < byte_offset:
            logger.info("Log file was reset (size decreased)")
            byte_offset = 0

        if server_size > byte_offset:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {current_file}", bio.write, rest=byte_offset)
            new_content = bio.getvalue().decode("utf-8", errors="ignore")
            return new_content, server_size, current_file

        return None, byte_offset, current_file
    except Exception as e:
        logger.error(f"FTP fetch error: {e}")
        # Forçar reconexão no próximo ciclo
        _persistent_ftp = None
        return None, byte_offset, current_file


# =============================================================================
# BACKGROUND TASKS
# =============================================================================


def _sync_ban_list_now():
    """Sync síncrono do ban.txt — chamado na startup do bot."""
    import sqlite3
    from ftplib import FTP

    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")
    if not all([ftp_host, ftp_user, ftp_pass]):
        logger.error("[BAN-SYNC] FTP credentials missing in .env")
        return

    _db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.db")
    conn = sqlite3.connect(_db)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT xuid FROM infractions
            WHERE auto_banned=1 AND ban_lifted=0
            AND xuid IS NOT NULL AND xuid != ''
        """)
        xuids_db = set(r[0] for r in cur.fetchall())
    finally:
        conn.close()

    ftp = FTP()
    try:
        ftp.connect(ftp_host, 21, timeout=10)
        ftp.login(ftp_user, ftp_pass)
        ftp.set_pasv(True)

        buf = io.BytesIO()
        try:
            ftp.retrbinary("RETR /dayzxb/config/ban.txt", buf.write)
            xuids_file = set(
                l.strip()
                for l in buf.getvalue().decode("utf-8", errors="ignore").split("\n")
                if l.strip()
            )
        except Exception:
            xuids_file = set()

        missing = xuids_db - xuids_file
        if missing:
            all_xuids = xuids_file | xuids_db
            upload_buf = io.BytesIO(("\n".join(all_xuids) + "\n").encode("utf-8"))
            ftp.storbinary("STOR /dayzxb/config/ban.txt", upload_buf)
            logger.warning(
                f"[BAN-SYNC] Startup: {len(missing)} XUIDs restaurados. Total: {len(all_xuids)}"
            )
        else:
            logger.info(f"[BAN-SYNC] Startup: ban.txt OK com {len(xuids_file)} XUIDs.")
    except Exception as e:
        logger.error(f"[BAN-SYNC] Erro no sync startup: {e}")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


@tasks.loop(hours=1)
async def sync_ban_list():
    """Sincroniza ban.txt com security.db a cada hora — mantém o banco como fonte de verdade."""
    import sqlite3
    from ftplib import FTP

    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")
    if not all([ftp_host, ftp_user, ftp_pass]):
        logger.error("[BAN-SYNC] FTP credentials missing in .env")
        return

    _db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.db")
    conn = sqlite3.connect(_db)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT xuid FROM infractions
            WHERE auto_banned=1 AND ban_lifted=0
            AND xuid IS NOT NULL AND xuid != ''
        """)
        xuids_db = set(r[0] for r in cur.fetchall())
    finally:
        conn.close()

    ftp = FTP()
    try:
        ftp.connect(ftp_host, 21, timeout=10)
        ftp.login(ftp_user, ftp_pass)
        ftp.set_pasv(True)

        buf = io.BytesIO()
        try:
            ftp.retrbinary("RETR /dayzxb/config/ban.txt", buf.write)
            xuids_file = set(
                l.strip()
                for l in buf.getvalue().decode("utf-8", errors="ignore").split("\n")
                if l.strip()
            )
        except Exception:
            xuids_file = set()

        missing = xuids_db - xuids_file
        if missing:
            all_xuids = xuids_file | xuids_db
            new_content = "\n".join(all_xuids) + "\n"
            upload_buf = io.BytesIO(new_content.encode("utf-8"))
            ftp.storbinary("STOR /dayzxb/config/ban.txt", upload_buf)
            logger.warning(
                f"[BAN-SYNC] ban.txt restaurado — {len(missing)} XUIDs faltavam. Total: {len(all_xuids)}"
            )
        else:
            logger.info(
                f"[BAN-SYNC] ban.txt OK — {len(xuids_file)} XUIDs sincronizados."
            )
    except Exception as e:
        logger.error(f"[BAN-SYNC] Erro na sincronização: {e}")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


@tasks.loop(seconds=3)
async def monitor_logs():
    """Main log monitoring loop - reads new lines from FTP and processes them."""
    global last_byte_offset, current_log_file

    new_content, new_offset, new_file = await asyncio.to_thread(
        _ftp_fetch_new_lines, current_log_file, last_byte_offset
    )

    # Salvar estado em disco sempre que offset ou arquivo mudar
    if new_offset != last_byte_offset or new_file != current_log_file:
        _save_log_state(new_file, new_offset)

    last_byte_offset = new_offset
    current_log_file = new_file

    if new_content:
        for line in new_content.split("\n"):
            stripped = line.strip()
            if stripped:
                await parse_log_line(stripped)

    # Periodic cleanup of in-memory trackers to prevent memory leaks
    cutoff = datetime.now(timezone.utc).timestamp() - 3600
    stale_positions = [k for k, v in _recent_player_positions.items() if v["t"] < cutoff]
    for k in stale_positions:
        del _recent_player_positions[k]
    stale_fires = [k for k, v in _fireplace_spam_tracker.items() if not v]
    for k in stale_fires:
        del _fireplace_spam_tracker[k]


_raid_toggled_this_hour = None

@tasks.loop(seconds=60)
async def raid_scheduler():
    """Master controller: gerencia modo pausa/raid.
    - Sabados 20h-22h BRT: ativa raid (base damage ON, construcao livre, tasks FTP)
    - Fora do horario: modo pausa (base damage OFF, construcao restrita, sem FTP)
    """
    global _raid_toggled_this_hour, _bot_paused
    br_now = datetime.now(timezone.utc) - timedelta(hours=3)

    raid_start = _server_config["raid_start_hour"]
    raid_end = _server_config["raid_end_hour"]

    # Fora de sabado: garantir que esta pausado
    if br_now.weekday() != 5:
        _raid_toggled_this_hour = None
        if not _bot_paused:
            logger.info("[RAID] Dia mudou - desativando modo raid")
            await _toggle_base_damage(enabled=False)
            await _toggle_free_building(free=False)
            await _stop_raid_tasks()
            await restart_nitrado()
            await notify_ban(
                "**RAID ENCERRADO!** Dano em bases bloqueado. "
                "Construcao restrita. Bot em modo pausa."
            )
        return

    current_key = (br_now.date(), br_now.hour)
    if current_key == _raid_toggled_this_hour:
        return

    # SABADO - Hora de iniciar o raid
    if br_now.hour == raid_start and br_now.minute < 2:
        _raid_toggled_this_hour = current_key
        logger.info(f"[RAID] INICIANDO RAID - {raid_start:02d}:00 BRT")
        await _start_raid_tasks()
        await _toggle_free_building(free=True)
        await _toggle_base_damage(enabled=True)
        await restart_nitrado()
        await notify_ban(
            f"**RAID INICIADO!**\n"
            f"Dano em bases **LIBERADO** ate as {raid_end:02d}:00 BRT!\n"
            f"Construcao **LIVRE** durante o raid.\n"
            f"Monitoramento de logs **ATIVO**."
        )

    # SABADO - Hora de encerrar o raid
    elif br_now.hour == raid_end and br_now.minute < 2:
        _raid_toggled_this_hour = current_key
        logger.info(f"[RAID] ENCERRANDO RAID - {raid_end:02d}:00 BRT")
        await _toggle_base_damage(enabled=False)
        await _toggle_free_building(free=False)
        await restart_nitrado()
        await _stop_raid_tasks()
        await notify_ban(
            "**RAID ENCERRADO!**\n"
            "Dano em bases **BLOQUEADO**.\n"
            "Construcao **RESTRITA**.\n"
            "Bot em **modo pausa** ate o proximo raid."
        )


async def _toggle_base_damage(enabled: bool):
    """Download gameplay config, toggle disableBaseDamage, upload and restart."""
    downloaded = await asyncio.to_thread(
        download_file, GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG
    )
    if not downloaded:
        return
    try:
        with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
            config = json.load(f)
        config.setdefault("GeneralData", {})["disableBaseDamage"] = not enabled
        with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
            json.dump(config, f, indent=4)
        uploaded = await asyncio.to_thread(
            upload_file, LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH
        )
        if uploaded:
            await restart_nitrado()
    except Exception as e:
        logger.error(f"Raid config toggle error: {e}")
    finally:
        if os.path.exists(LOCAL_GAMEPLAY_CONFIG):
            os.remove(LOCAL_GAMEPLAY_CONFIG)


async def _start_raid_tasks():
    """Inicia tasks FTP/Nitrado para o periodo de raid."""
    global _bot_paused, last_byte_offset
    _bot_paused = False
    last_byte_offset = -1  # Flag: pular para fim do arquivo (ignorar logs antigos)
    logger.info("[PAUSE] === ATIVANDO MODO RAID ===")

    if not monitor_logs.is_running():
        monitor_logs.start()
        logger.info("[PAUSE] monitor_logs INICIADO")
    if not sync_ban_list.is_running():
        sync_ban_list.start()
        logger.info("[PAUSE] sync_ban_list INICIADO")
    if not ftp_health_monitor.is_running():
        ftp_health_monitor.start()
        logger.info("[PAUSE] ftp_health_monitor INICIADO")
    if not monitor_device_ids.is_running():
        monitor_device_ids.start()
        logger.info("[PAUSE] monitor_device_ids INICIADO")


async def _stop_raid_tasks():
    """Para tasks FTP/Nitrado apos o raid."""
    global _bot_paused
    _bot_paused = True
    logger.info("[PAUSE] === DESATIVANDO MODO RAID ===")

    for task_obj, name in [
        (monitor_logs, "monitor_logs"),
        (sync_ban_list, "sync_ban_list"),
        (ftp_health_monitor, "ftp_health_monitor"),
        (monitor_device_ids, "monitor_device_ids"),
    ]:
        if task_obj.is_running():
            task_obj.cancel()
            logger.info(f"[PAUSE] {name} PARADO")


async def _toggle_free_building(free: bool):
    """Toggle construcao livre (free=True) ou restrita (free=False)."""
    downloaded = await asyncio.to_thread(
        download_file, GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG
    )
    if not downloaded:
        logger.error("[BUILD] Nao foi possivel baixar cfggameplay.json")
        return
    try:
        with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
            config = json.load(f)

        if "BaseBuildingData" not in config:
            config["BaseBuildingData"] = {}
        if "HologramData" not in config["BaseBuildingData"]:
            config["BaseBuildingData"]["HologramData"] = {}
        hologram = config["BaseBuildingData"]["HologramData"]

        keys = [
            "disableIsCollidingBBoxCheck",
            "disableIsCollidingPlayerCheck",
            "disableIsClippingRoofCheck",
            "disableIsBaseViableCheck",
            "disableIsCollidingGPlotCheck",
            "disableIsCollidingAngleCheck",
            "disableIsPlacementPermittedCheck",
            "disableHeightPlacementCheck",
            "disableIsUnderwaterCheck",
            "disableIsInTerrainCheck",
            "disableColdAreaBuildingCheck",
        ]
        for key in keys:
            hologram[key] = free

        with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
            json.dump(config, f, indent=4)

        uploaded = await asyncio.to_thread(
            upload_file, LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH
        )
        if uploaded:
            mode = "LIVRE" if free else "RESTRITA"
            logger.info(f"[BUILD] Construcao {mode} aplicada no cfggameplay.json")
    except Exception as e:
        logger.error(f"[BUILD] Erro ao toggle free building: {e}")
    finally:
        if os.path.exists(LOCAL_GAMEPLAY_CONFIG):
            os.remove(LOCAL_GAMEPLAY_CONFIG)


@tasks.loop(minutes=5)
async def monitor_truck_spawns():
    """Scan for newly available trucks at spawn points."""
    global last_available_trucks
    temp_local = "truck_availability_temp.json"
    try:
        downloaded = await asyncio.to_thread(
            download_file, "truck_availability.json", temp_local
        )
        if not downloaded:
            return
        with open(temp_local, "r") as f:
            data = json.load(f)
        if "items" not in data:
            return
        current_trucks = set()
        for item in data["items"]:
            parts = item["coords"].split()
            if len(parts) >= 3:
                tx, tz = int(float(parts[0])), int(float(parts[2]))
                current_trucks.add((tx, tz))
        new_trucks = current_trucks - last_available_trucks
        for truck in new_trucks:
            await notify_truck_alert(
                f"**CAMINHAO DISPONIVEL!**\n"
                f"Um novo Caminhao de Kit foi detectado!\n"
                f"Local: `[{truck[0]}, {truck[1]}]`\n*Corra para garantir o seu!*"
            )
        last_available_trucks = current_trucks
    except Exception as e:
        logger.error(f"Truck spawn scan error: {e}")
    finally:
        if os.path.exists(temp_local):
            os.remove(temp_local)


@tasks.loop(seconds=30)
async def check_truck_timers():
    """Check truck expiry timers and send deletion commands."""
    now = datetime.now(timezone.utc)
    to_delete = []

    for coords, data in list(active_truck_timers.items()):
        remaining = (data["expiry"] - now).total_seconds()
        if 540 <= remaining <= 600 and not data["warning_sent"]:
            await notify_truck_alert(
                f"**AVISO**: O caminhao pego por **{data['player']}** em `{coords}` "
                f"desaparecera em **10 minutos**!"
            )
            data["warning_sent"] = True
        if remaining <= 0:
            to_delete.append(coords)

    if to_delete:
        deletion_items = [{"coords": f"{c[0]} 0 {c[1]}"} for c in to_delete]
        payload = {"items": deletion_items}
        temp_file = "deletions_temp.json"
        try:
            with open(temp_file, "w") as f:
                json.dump(payload, f)
            uploaded = await asyncio.to_thread(upload_file, temp_file, "deletions.json")
            for c in to_delete:
                if uploaded:
                    await notify_truck_alert(
                        f"**REMOCAO**: O caminhao de `{c}` expirou e foi removido!"
                    )
                del active_truck_timers[c]
            if uploaded:
                logger.info(f"Truck deletion command sent for {len(to_delete)} trucks")
        except Exception as e:
            logger.error(f"Truck deletion error: {e}")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


# =============================================================================
# NEW TASKS: Rate-limit Queue / FTP Health / DB Backup
# =============================================================================


@tasks.loop(seconds=1)
async def drain_ban_queue():
    """Drains the ban notification queue at 1 message/second to avoid Discord rate-limits."""
    try:
        message = _ban_notify_queue.get_nowait()
        await _notify_ban_direct(message)
    except asyncio.QueueEmpty:
        pass
    except Exception as e:
        logger.warning(f"[QUEUE] Erro ao enviar notificação: {e}")


@tasks.loop(minutes=5)
async def ftp_health_monitor():
    """Checks FTP connectivity every 5 minutes. Alerts admins after 3 consecutive failures."""
    global _ftp_fail_count, _ftp_health_alert_sent
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")
    ftp_port = int(os.getenv("FTP_PORT", 21))

    if not all([ftp_host, ftp_user, ftp_pass]):
        return

    try:
        import ftplib
        ftp = ftplib.FTP()
        ftp.connect(ftp_host, ftp_port, timeout=10)
        ftp.login(ftp_user, ftp_pass)
        ftp.quit()
        # FTP OK — reset counters
        if _ftp_fail_count > 0:
            logger.info(f"[FTP-HEALTH] Conexão restaurada após {_ftp_fail_count} falhas.")
            if _ftp_health_alert_sent and BAN_CHANNEL_ID:
                try:
                    channel = bot.get_channel(int(BAN_CHANNEL_ID))
                    if channel:
                        await channel.send(
                            "✅ **FTP RESTAURADO** — Conexão com o servidor Nitrado normalizada. "
                            "Monitoramento de logs retomado."
                        )
                except Exception:
                    pass
        _ftp_fail_count = 0
        _ftp_health_alert_sent = False
    except Exception as e:
        _ftp_fail_count += 1
        logger.warning(f"[FTP-HEALTH] Falha de conexão FTP #{_ftp_fail_count}: {e}")
        # Alert after 3 consecutive failures (15 minutes offline)
        if _ftp_fail_count >= 3 and not _ftp_health_alert_sent:
            _ftp_health_alert_sent = True
            alert_msg = (
                f"⚠️ **ALERTA: FTP OFFLINE**\n"
                f"O bot falhou {_ftp_fail_count}x ao conectar ao servidor Nitrado via FTP.\n"
                f"**Os logs NÃO estão sendo monitorados!**\n"
                f"Erro: `{e}`\n"
                f"_O bot continuará tentando automaticamente._"
            )
            if BAN_CHANNEL_ID:
                try:
                    channel = bot.get_channel(int(BAN_CHANNEL_ID))
                    if channel:
                        await channel.send(alert_msg)
                except Exception as ex:
                    logger.error(f"[FTP-HEALTH] Não foi possível enviar alerta: {ex}")
            logger.error(f"[FTP-HEALTH] ALERTA ENVIADO: FTP offline há {_ftp_fail_count * 5} minutos!")


_backup_sent_today = None  # Guarda a data do último backup enviado

@tasks.loop(hours=1)
async def backup_database():
    """Daily backup: uploads security.db as a Discord file attachment to the admin channel."""
    global ADMIN_BACKUP_CHANNEL_ID, _backup_sent_today
    # Executar somente às 07:00 UTC (04:00 BRT)
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour != 7:
        return
    # Evitar enviar mais de uma vez no mesmo dia
    today = now_utc.strftime("%Y-%m-%d")
    if _backup_sent_today == today:
        return


    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.db")
    if not os.path.exists(db_path):
        logger.warning("[BACKUP] security.db não encontrado. Backup ignorado.")
        return

    channel_id = ADMIN_BACKUP_CHANNEL_ID or BAN_CHANNEL_ID
    if not channel_id:
        logger.warning("[BACKUP] Canal de backup não configurado. Use ADMIN_BACKUP_CHANNEL_ID no .env")
        return

    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            channel = await bot.fetch_channel(int(channel_id))
        if not channel:
            logger.error("[BACKUP] Canal de backup não encontrado.")
            return

        db_size_kb = os.path.getsize(db_path) // 1024
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"security_backup_{timestamp}.db"

        with open(db_path, "rb") as f:
            await channel.send(
                content=(
                    f"🗄️ **BACKUP AUTOMÁTICO DO BANCO DE DADOS**\n"
                    f"Data: `{timestamp}` | Tamanho: `{db_size_kb} KB`\n"
                    f"Salve este arquivo em local seguro."
                ),
                file=discord.File(f, filename=filename),
            )
        _backup_sent_today = today
        logger.info(f"[BACKUP] Backup enviado ao canal {channel_id} ({db_size_kb} KB)")
    except Exception as e:
        logger.error(f"[BACKUP] Erro ao enviar backup: {e}")


# =============================================================================
# DEVICE ID MONITOR — Captura Device IDs do script log via FTP
# =============================================================================

# Estado do monitor de Device IDs (lê RPT para linhas [MAM] com Device IDs)
_device_rpt_offset = 0
_device_rpt_file = None
_mam_ftp = None  # Conexão FTP dedicada do monitor MAM


def _find_latest_rpt(ftp):
    """Encontra o RPT mais recente no FTP."""
    try:
        ftp.cwd("/dayzxb/config")
        ftp.voidcmd("TYPE I")
        items = ftp.nlst()
        rpts = [f for f in items if f.endswith(".RPT")]
        if rpts:
            rpts.sort(reverse=True)
            return rpts[0]
    except Exception as e:
        logger.error(f"[MAM] Error finding RPT: {e}")
    return None



def _get_mam_ftp():
    """Conexão FTP exclusiva do monitor MAM — isolada do _persistent_ftp principal."""
    global _mam_ftp
    if _mam_ftp is not None:
        try:
            _mam_ftp.voidcmd("NOOP")
            return _mam_ftp
        except Exception:
            _mam_ftp = None
    _mam_ftp = connect_ftp()
    return _mam_ftp

def _ftp_fetch_rpt_data(current_file, byte_offset):
    """Lê novas linhas do RPT via FTP (busca [MAM] device entries)."""
    ftp = _get_mam_ftp()
    if not ftp:
        return None, byte_offset, current_file
    try:
        latest = _find_latest_rpt(ftp)
        if not latest:
            return None, byte_offset, current_file

        # RPT changed (server restart) — read full new file
        if latest != current_file:
            ftp.voidcmd("TYPE I")
            file_size = ftp.size(latest)
            if file_size > 0:
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {latest}", bio.write)
                new_content = bio.getvalue().decode("utf-8", errors="ignore")
                return new_content, file_size, latest
            return None, 0, latest

        ftp.voidcmd("TYPE I")
        server_size = ftp.size(current_file)

        # File truncated (shouldn't happen with RPT, but just in case)
        if server_size < byte_offset:
            byte_offset = 0

        # New data available — read only the new bytes
        if server_size > byte_offset:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {current_file}", bio.write, rest=byte_offset)
            new_content = bio.getvalue().decode("utf-8", errors="ignore")
            return new_content, server_size, current_file

        return None, byte_offset, current_file
    except Exception as e:
        logger.error(f"[MAM] FTP fetch error: {e}")
        global _mam_ftp
        _mam_ftp = None
        return None, byte_offset, current_file


# =============================================================================
# Regex para capturar Device IDs das linhas [MAM] no RPT
# Formatos esperados:
#   [MAM] :: [NetworkServer::CheckMAMData] :: device: BASE64= | account: HEX40 | time: N
#   [MAM] :: [NetworkServer::RegisterMAMData] :: device: BASE64= | account: HEX40 | time: N
#   [MAM] :: [NetworkServer::RegisterMAMDataHelper] :: id1: BASE64= | id2: HEX40 | time: N
# =============================================================================
_MAM_DEVICE_RE = re.compile(r'device:\s*([^\s|]+)')
_MAM_ACCOUNT_RE = re.compile(r'account:\s*([^\s|]+)')
_MAM_ID1_RE = re.compile(r'id1:\s*([^\s|]+)')
_MAM_ID2_RE = re.compile(r'id2:\s*([^\s|]+)')

# Regex para associar Device ID ao gamertag via StateMachine (uid = XUID)
_STATEMACHINE_RE = re.compile(
    r'\[StateMachine\]: Player\s+(.+?)\s+\(dpnid\s+\d+\s+uid\s+([A-Fa-f0-9]{40})\)'
)

# Cache de XUID → gamertag (preenchido via StateMachine/ADM no mesmo RPT)
_xuid_to_gamertag = {}


@tasks.loop(seconds=30)
async def monitor_device_ids():
    """Monitora RPT logs para capturar Device IDs via [MAM] entries."""
    global _device_rpt_offset, _device_rpt_file, _xuid_to_gamertag

    new_content, new_offset, new_file = await asyncio.to_thread(
        _ftp_fetch_rpt_data, _device_rpt_file, _device_rpt_offset
    )

    # Se mudou de arquivo (server restart), limpar cache de gamertags
    if new_file != _device_rpt_file:
        _xuid_to_gamertag = {}

    _device_rpt_offset = new_offset
    _device_rpt_file = new_file

    if not new_content:
        return

    lines = new_content.splitlines()
    device_count = 0

    for line in lines:
        # 1) Manter cache de XUID → Gamertag via StateMachine entries
        sm = _STATEMACHINE_RE.search(line)
        if sm:
            gt = sm.group(1).strip()
            uid = sm.group(2).strip()
            if gt and uid:
                _xuid_to_gamertag[uid] = gt

        # 2) Capturar Device IDs das linhas [MAM]
        if "[MAM]" not in line:
            continue

        # Validar que é uma linha MAM com dados de device
        has_network = ("CheckMAMData" in line or "RegisterMAMData" in line)
        if not has_network:
            continue

        device_id = None
        xuid = None

        # Tentar formato padrão: device: ... | account: ...
        dm = _MAM_DEVICE_RE.search(line)
        am = _MAM_ACCOUNT_RE.search(line)
        if dm and am:
            device_id = dm.group(1).strip()
            xuid = am.group(1).strip()
        else:
            # Tentar formato alternativo: id1: ... | id2: ...
            i1 = _MAM_ID1_RE.search(line)
            i2 = _MAM_ID2_RE.search(line)
            if i1 and i2:
                device_id = i1.group(1).strip()
                xuid = i2.group(1).strip()

        if not device_id or not xuid or len(device_id) < 5 or len(xuid) < 10:
            continue

        # Buscar gamertag do cache StateMachine
        gamertag = _xuid_to_gamertag.get(xuid, None)

        # Se não temos gamertag no cache, tentar buscar do banco
        if not gamertag:
            try:
                existing = database.get_player_identity_by_xuid(xuid)
                if existing:
                    gamertag = existing.get("gamertag", None)
            except Exception:
                pass

        # Salvar no banco mesmo sem gamertag (XUID + Device ID é o essencial)
        try:
            database.update_player_identity(
                gamertag=gamertag or f"XUID_{xuid[:8]}",
                xuid=xuid,
                ip=None,
                device_id=device_id
            )
            device_count += 1
            if gamertag:
                logger.debug(f"[MAM] Device ID capturado: {gamertag} → {device_id[:20]}...")
        except Exception as e:
            logger.error(f"[MAM] DB error for XUID {xuid[:8]}: {e}")

    if device_count > 0:
        logger.info(f"[MAM] {device_count} Device IDs capturados do RPT e salvos no banco")


# =============================================================================
# DISCORD MODALS (Interactive UI)
# =============================================================================


def _modal_on_error(modal_name):
    """Retorna handler on_error padrão para modais — suprime interações expiradas (10062)."""

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if (
            isinstance(error, discord.errors.NotFound)
            and getattr(error, "code", None) == 10062
        ):
            logger.debug(f"[MODAL] {modal_name}: interação expirada ignorada")
            return
        logger.error(f"[MODAL] {modal_name} erro: {error}", exc_info=error)

    return on_error


class LinkGamertagModal(ui.Modal, title="Vincular Gamertag"):
    gamertag = ui.TextInput(
        label="Sua Gamertag (Xbox)",
        placeholder="Ex: Player123",
        min_length=3,
        max_length=20,
    )
    on_error = _modal_on_error("LinkGamertagModal")

    async def on_submit(self, interaction: discord.Interaction):
        discord_id = interaction.user.id
        gt = self.gamertag.value

        # Check if gamertag is already linked to another Discord user
        existing = database.get_discord_id_by_gamertag(gt)
        if existing and str(existing) != str(discord_id):
            return await interaction.response.send_message(
                f"A Gamertag `{gt}` ja esta vinculada a outro usuario.", ephemeral=True
            )

        # Check if user already has a different gamertag
        existing_gt = database.get_gamertag_by_discord(discord_id)
        if existing_gt and existing_gt != gt:
            database.update_gamertag_link(discord_id, gt)
            await interaction.response.send_message(
                f"Sua Gamertag foi atualizada para `{gt}`!", ephemeral=True
            )
            await notify_admin_log(
                f"**Gamertag Atualizada**: {interaction.user.display_name} mudou para `{gt}`."
            )
            return

        database.create_discord_link_247(discord_id, gt)

        # Assign verified role
        if VERIFIED_ROLE_ID and _can_assign_roles:
            try:
                role = interaction.guild.get_role(int(VERIFIED_ROLE_ID))
                if role:
                    await interaction.user.add_roles(role)
            except Exception as e:
                logger.warning(f"Could not assign verified role: {e}")

        await interaction.response.send_message(
            f"**Registro Concluido!** Sua Gamertag `{gt}` foi vinculada com sucesso.",
            ephemeral=True,
        )
        await notify_admin_log(
            f"**Nova Gamertag**: {interaction.user.display_name} vinculou `{gt}`."
        )


class CreateClanModal(ui.Modal, title="Registrar Novo Cla"):
    clan_name = ui.TextInput(
        label="Nome do Cla",
        placeholder="Ex: Os Justiceiros",
        min_length=3,
        max_length=20,
    )
    on_error = _modal_on_error("CreateClanModal")

    async def on_submit(self, interaction: discord.Interaction):
        leader_id = interaction.user.id
        gt = database.get_gamertag_by_discord(leader_id)
        if not gt:
            return await interaction.response.send_message(
                "Vincule sua Gamertag primeiro!", ephemeral=True
            )
        if database.get_clan_by_leader(leader_id):
            return await interaction.response.send_message(
                "Voce ja e lider de um cla!", ephemeral=True
            )
        clan_id = database.create_clan_247(self.clan_name.value, leader_id)
        if clan_id:
            database.add_clan_member(clan_id, leader_id, gt)
            await interaction.response.send_message(
                f"Cla **{self.clan_name.value}** criado com sucesso!", ephemeral=True
            )
            await notify_admin_log(
                f"**Novo Cla**: {interaction.user.display_name} criou **{self.clan_name.value}** via Portal."
            )
        else:
            await interaction.response.send_message(
                "Esse nome de cla ja existe.", ephemeral=True
            )


class AddMemberModal(ui.Modal, title="Convidar Membro para o Clã"):
    gamertag = ui.TextInput(
        label="Gamertag do Amigo",
        placeholder="Ex: PlayerFriend123",
        min_length=3,
        max_length=20,
    )
    on_error = _modal_on_error("AddMemberModal")

    async def on_submit(self, interaction: discord.Interaction):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "Apenas o líder pode convidar membros.", ephemeral=True
            )

        # Process multiple gamertags separated by comma
        raw_gamertags = self.gamertag.value.replace(";", ",").split(",")
        gamertags = [gt.strip() for gt in raw_gamertags if gt.strip()]

        if not gamertags:
            return await interaction.response.send_message(
                "Digite ao menos uma Gamertag válida.", ephemeral=True
            )

        results = []
        for gt in gamertags:
            if database.create_clan_invite(clan_info["id"], gt):
                results.append(f"✅ `{gt}`: Convite enviado!")
                await notify_admin_log(
                    f"**Convite Enviado**: {interaction.user.display_name} convidou "
                    f"`{gt}` para o clã **{clan_info['name']}**."
                )
            else:
                results.append(f"⚠️ `{gt}`: Convite já pendente.")

        # Final report to the leader
        report = "**Relatório de Convites:**\n" + "\n".join(results)
        await interaction.response.send_message(report, ephemeral=True)


class DissolveClanModal(ui.Modal, title="CANCELAR REGISTROS (DELETAR CLA)"):
    confirm = ui.TextInput(
        label="Digite 'DELETAR' para confirmar",
        placeholder="DELETAR",
        min_length=7,
        max_length=7,
    )
    on_error = _modal_on_error("DissolveClanModal")

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "DELETAR":
            return await interaction.response.send_message(
                "Confirmacao incorreta. O cla nao foi deletado.", ephemeral=True
            )
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "Voce nao e lider de nenhum cla.", ephemeral=True
            )
        if database.delete_clan_by_leader(interaction.user.id):
            await interaction.response.send_message(
                f"**Registros Cancelados!** O cla **{clan_info['name']}** foi removido. "
                f"Voce ja pode criar um novo cla.",
                ephemeral=True,
            )
            await notify_admin_log(
                f"**Cla Deletado**: {interaction.user.display_name} dissolveu **{clan_info['name']}**."
            )
        else:
            await interaction.response.send_message(
                "Ocorreu um erro ao tentar deletar o cla.", ephemeral=True
            )


# =============================================================================
# CLAN PORTAL VIEW (Persistent Buttons)
# =============================================================================


# =============================================================================
# NEW SEPARATED PORTAL VIEWS
# =============================================================================


class LeaderPortalView(ui.View):
    """View for Clan Leaders to manage their clan."""

    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item
    ) -> None:
        if (
            isinstance(error, discord.errors.NotFound)
            and getattr(error, "code", None) == 10062
        ):
            return
        await super().on_error(interaction, error, item)

    @ui.button(
        label="🔗 Vincular Gamertag",
        style=discord.ButtonStyle.blurple,
        custom_id="portal:leader_link_gt",
    )
    async def link_gt(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LinkGamertagModal())

    @ui.button(
        label="🚩 Registrar Meu Clã",
        style=discord.ButtonStyle.success,
        custom_id="portal:create_clan",
    )
    async def create_clan(self, interaction: discord.Interaction, button: ui.Button):
        gt = database.get_gamertag_by_discord(interaction.user.id)
        if not gt:
            return await interaction.response.send_message(
                "Você precisa vincular sua Gamertag primeiro no **Portal de Membros** abaixo!",
                ephemeral=True,
            )
        await interaction.response.send_modal(CreateClanModal())

    @ui.button(
        label="➕ Convidar Amigo",
        style=discord.ButtonStyle.primary,
        custom_id="portal:invite_member",
    )
    async def invite_member(self, interaction: discord.Interaction, button: ui.Button):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "Você precisa ser líder de um clã para convidar membros!",
                ephemeral=True,
            )
        await interaction.response.send_modal(AddMemberModal())

    @ui.button(
        label="🗑️ DELETAR MEU CLÃ",
        style=discord.ButtonStyle.danger,
        custom_id="portal:dissolve_clan",
    )
    async def dissolve_clan(self, interaction: discord.Interaction, button: ui.Button):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "Apenas líderes de clã podem acessar esta opção.", ephemeral=True
            )
        await interaction.response.send_modal(DissolveClanModal())


class MemberPortalView(ui.View):
    """View for all players to link GT and accept invites."""

    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item
    ) -> None:
        if (
            isinstance(error, discord.errors.NotFound)
            and getattr(error, "code", None) == 10062
        ):
            return
        await super().on_error(interaction, error, item)

    @ui.button(
        label="🔗 Vincular Gamertag",
        style=discord.ButtonStyle.blurple,
        custom_id="portal:link_gt",
    )
    async def link_gt(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LinkGamertagModal())

    @ui.button(
        label="📩 Aceitar Convite",
        style=discord.ButtonStyle.secondary,
        custom_id="portal:accept_invite",
    )
    async def accept_invite(self, interaction: discord.Interaction, button: ui.Button):
        gt = database.get_gamertag_by_discord(interaction.user.id)
        if not gt:
            return await interaction.response.send_message(
                "Você precisa vincular sua Gamertag primeiro!", ephemeral=True
            )

        invites = database.get_pending_invites(gt)
        if not invites:
            return await interaction.response.send_message(
                "Você não possui convites pendentes.", ephemeral=True
            )

        # Take the most recent invite
        invite = invites[0]
        database.add_clan_member(invite["clan_id"], interaction.user.id, gt)
        database.delete_invite(invite["id"])

        await interaction.response.send_message(
            f"✅ Sucesso! Agora você faz parte do clã **{invite['clan_name']}**.",
            ephemeral=True,
        )
        await notify_admin_log(
            f"**Convite Aceito**: {interaction.user.display_name} ({gt}) entrou no clã **{invite['clan_name']}**."
        )


# =============================================================================
# COMMANDS
# =============================================================================


@bot.command(name="portal_view")
@commands.has_permissions(administrator=True)
async def setup_portal_view(ctx):
    """Configura os portais de Liderança e Membros (Auto-post)."""
    embed_header, embed_member, embed_leader = _build_portal_embeds()
    await ctx.send(embed=embed_header)
    await ctx.send(embed=embed_member, view=MemberPortalView())
    await ctx.send(embed=embed_leader, view=LeaderPortalView())
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


def _build_portal_embeds():
    """Retorna os 3 embeds do portal: header, membros e líderes."""

    # ── Embed 1: Header explicativo (sem botões) ──
    embed_header = discord.Embed(
        title="🎮  BRASIL SUL — DayZ Xbox  |  Cadastro de Clã",
        description=(
            "Sua base só é **protegida pelo bot** após o cadastro do seu clã.\n"
            "**Sem cadastro = sem proteção.** Qualquer jogador pode construir no seu território "
            "e não será punido automaticamente.\n\n"
            "⏱️ **Leva menos de 2 minutos. Siga o passo a passo abaixo.**"
        ),
        color=discord.Color.gold(),
    )
    embed_header.set_footer(text="Sistema 24/7 Security — BigodeTexas")

    # ── Embed 2: Portal do Membro ──
    embed_member = discord.Embed(
        title="👤  SOU MEMBRO DE CLÃ",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**1️⃣  Vincule seu Xbox**\n"
            "└ Clique no botão 🔗 **Vincular Xbox** abaixo\n"
            "└ Digite sua **Gamertag exata** do Xbox\n\n"
            "**2️⃣  Aguarde o convite**\n"
            "└ Peça ao **líder do seu clã** para te convidar\n"
            "└ *(O líder usa o botão 📨 Convidar Membro)*\n\n"
            "**3️⃣  Aceite o convite**\n"
            "└ Clique no botão ✅ **Aceitar Convite** abaixo\n"
            "└ Pronto! Você estará liberado para construir na base do clã\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *Você precisa estar vinculado antes de aceitar convites.*"
        ),
        color=discord.Color.blue(),
    )

    # ── Embed 3: Portal do Líder ──
    embed_leader = discord.Embed(
        title="🚩  SOU LÍDER DE CLÃ",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**1️⃣  Vincule seu Xbox** *(obrigatório primeiro!)*\n"
            "└ Clique no botão 🔗 **Vincular Xbox** abaixo\n"
            "└ Digite sua **Gamertag exata** do Xbox\n\n"
            "**2️⃣  Registre seu Clã**\n"
            "└ Clique no botão 🏰 **Registrar Clã**\n"
            "└ Escolha um nome único para o seu grupo\n\n"
            "**3️⃣  Convide seus membros**\n"
            "└ Clique em 📨 **Convidar Membro** e marque o @ do amigo\n"
            "└ Ele receberá o convite e poderá aceitar aqui neste canal\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *Após o registro, invasores são banidos automaticamente.*"
        ),
        color=discord.Color.dark_green(),
    )

    return embed_header, embed_member, embed_leader


@bot.command(name="regras")
async def regras(ctx):
    """Display the official server rules."""

    # Text content separated for better formatting
    desc = (
        "**ESTAR PERMITIDO**\n"
        "✅ CONSTRUCAO DE BASES EM AREAS MILITARES COM EXECAO AO BUNKER QUE ESTAR LOCALIZADO PROX. DO NAVIO TOXICO.\n"
        "✅ RAID TATICO\n"
        "✅ ROLETAR CADEADO\n\n"
        "**ESTAR PROIBIDO (BANIMENTO PERMANENTE VIA ID - XBOX)**\n"
        "❌ CRIAR PLANTACAO (GARDEN)\n"
        "❌ CRIAR MAIS DE 2 FOGUEIRA (INTERVALO DE 1HORA)\n"
        "❌ MOVIMENTAR TAMBORES MAIS DE 8 VEZES\n"
        "❌ CRIAR GLICH COM EMOTES\n\n"
        "**OBSERVACOES**\n"
        "**1.** EXISTE BANIMENTO POR CONSTRUCOES EM BASES REGISTRADAS OU SEJA, NAO CONSTRUA EM AREA DE BASE E NAO USE, BARRACAS, TAMBORES, BAU MARINHO.\n\n"
        "**2.** PARA QUEM DESEJA CADASTAR BASE DEVERA ENTRAR NO CANAL (CADASTRO DE CLAN) E FAZER O CADASTRO DO LIDER E DEPOIS SEGUIR A SEQUENCIA DO CADASTRO.\n\n"
        "**3.** NA AREA DE CADASTRO EXISTE A AREA PARA OS MEMBROS, ELES DEVEM CADASTRAR A GAME TAG QUE O LIDER CADASTROU E CONFIRMAR E LOGO ESTARA LIBERADO PARA INTERAGIR NA BASE DO CLAN.\n\n"
        "**🚛 CAMINHAO KIT BASE**\n"
        "EXISTE CAMINHOES COM MATERIAIS DE CONSTRUCAO PARA DAR AQUELA FORCA.\n\n"
        "**⚔️ DIAS DE RAID**\n"
        "SABADOS DAS 20 AS 22 HORAS.\n\n"
        "**🔗 LINKS ÚTEIS**\n"
        "📰 **Notícias:** [Entrar no Canal do Whatsapp](https://www.whatsapp.com/channel/0029Vb7QWlDKwqSJeEzNRK1H)\n"
        "💬 **Resenha (Faca):** [Entrar no Grupo do Whatsapp](https://chat.whatsapp.com/FH1allBJZp2AlV9ApnuImR?mode=gi_t)\n"
        "🚀 **Discord:** tiny.cc/brasil-sul-dayz"
    )

    embed = discord.Embed(
        title="REGRAS OFICIAIS - BRASIL SUL",
        description=desc,
        color=discord.Color.dark_red(),
    )
    embed.set_footer(text="Servidor DayZ 24/7 Security System")
    await ctx.send(embed=embed)
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


@bot.command(name="vincular")
async def vincular(ctx, gamertag: str):
    """Link your Discord to a Gamertag."""
    database.create_discord_link_247(ctx.author.id, gamertag)
    await ctx.send(
        f"**{ctx.author.display_name}**, seu Gamertag **{gamertag}** foi vinculado com sucesso!"
    )


@bot.group(name="clan", invoke_without_command=True)
async def clan(ctx):
    """Clan management commands."""
    await ctx.send(
        "**Comandos de Cla:**\n"
        "`!clan criar <nome>` - Cria um novo cla\n"
        "`!clan convidar @membro` - Envia convite\n"
        "`!clan aceitar` - Aceita convite pendente\n"
        "`!clan recusar` - Recusa convites\n"
        "`!clan lista` - Lista todos os clas\n"
        "`!clan sair` - Sai do cla atual"
    )


@clan.command(name="criar")
async def clan_criar(ctx, *, name: str):
    """Create a new clan."""
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send("Voce precisa usar `!vincular <gamertag>` primeiro.")
    if database.get_clan_by_leader(ctx.author.id):
        return await ctx.send("Voce ja e lider de um cla!")
    clan_id = database.create_clan_247(name, ctx.author.id)
    if clan_id:
        database.add_clan_member(clan_id, ctx.author.id, gt)
        await ctx.send(f"Cla **{name}** criado com sucesso!")
        await notify_admin_log(
            f"**Novo Cla**: {ctx.author.display_name} criou **{name}**."
        )
    else:
        await ctx.send("Esse nome de cla ja existe.")


@clan.command(name="convidar")
async def clan_convidar(ctx, member: discord.Member):
    """Invite a member to your clan."""
    clan_info = database.get_clan_by_leader(ctx.author.id)
    if not clan_info:
        return await ctx.send("Apenas o lider do cla pode convidar membros.")
    gt = database.get_gamertag_by_discord(member.id)
    if not gt:
        return await ctx.send(
            f"{member.mention} precisa usar `!vincular <gamertag>` primeiro."
        )
    if database.create_clan_invite(clan_info["id"], gt):
        await ctx.send(
            f"{member.mention}, voce foi convidado para o cla **{clan_info['name']}**!\n"
            f"Use `!clan aceitar` para entrar."
        )
    else:
        await ctx.send(
            "Nao foi possivel enviar o convite (talvez ja exista um pendente)."
        )


@clan.command(name="aceitar")
async def clan_aceitar(ctx):
    """Accept a pending clan invite."""
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send("Voce precisa usar `!vincular <gamertag>` antes de aceitar.")
    invites = database.get_pending_invites(gt)
    if not invites:
        return await ctx.send("Voce nao tem convites pendentes.")
    invite = invites[0]
    database.add_clan_member(invite["clan_id"], ctx.author.id, gt)
    database.delete_invite(invite["id"])
    await ctx.send(f"Bem-vindo ao cla **{invite['clan_name']}**, {ctx.author.mention}!")
    await notify_admin_log(
        f"**Membro Adicionado**: {ctx.author.display_name} ({gt}) entrou no cla **{invite['clan_name']}**."
    )


@clan.command(name="recusar")
async def clan_recusar(ctx):
    """Decline all pending clan invites."""
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send(
            "Voce precisa vincular sua Gamertag antes de recusar convites."
        )
    invites = database.get_pending_invites(gt)
    if not invites:
        return await ctx.send("Voce nao tem convites pendentes.")
    for invite in invites:
        database.delete_invite(invite["id"])
    await ctx.send("Todos os convites foram recusados.")


@clan.command(name="lista")
async def clan_lista(ctx):
    """List all registered clans."""
    clans = database.get_all_clans()
    if not clans:
        return await ctx.send("Nenhum cla registrado ainda.")
    msg = "**Clas Registrados:**\n"
    for c in clans:
        leader = ctx.guild.get_member(int(c["leader"]))
        leader_name = leader.display_name if leader else "Desconhecido"
        msg += f"- **{c['name']}** (Lider: {leader_name})\n"
    await ctx.send(msg)


@bot.command(name="setup_portal")
@commands.has_permissions(administrator=True)
async def setup_portal_minimal(ctx):
    """Configura o canal de portal interativo (admin only)."""
    everyone = ctx.guild.default_role
    overwrites = {
        everyone: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=False,
        ),
        ctx.guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            embed_links=True,
        ),
    }
    await ctx.channel.edit(overwrites=overwrites)
    await setup_portal_view(ctx)  # Calls the dual portal setup
    # ctx.message.delete() already called inside setup_portal_view


@bot.group(name="base", invoke_without_command=True)
async def base_cmd(ctx):
    """Base management commands."""
    await ctx.send(
        "**Comandos de Base:**\n"
        "`!base autorizar @amigo` - Autoriza um amigo na sua base\n"
        "`!base remover @amigo` - Remove autorizacao"
    )


@base_cmd.command(name="autorizar")
async def base_autorizar(ctx, member: discord.Member):
    """Authorize a friend in your base."""
    bases = database.get_security_bases()
    author_gt = database.get_gamertag_by_discord(ctx.author.id)
    owned_bases = [
        b
        for b in bases
        if b["owner_discord_id"] == str(ctx.author.id) or b["owner"] == author_gt
    ]
    if not owned_bases:
        return await ctx.send("Voce nao e proprietario de nenhuma base registrada.")
    guest_gt = database.get_gamertag_by_discord(member.id)
    if not guest_gt:
        return await ctx.send(f"{member.mention} precisa usar `!vincular` primeiro.")
    for b in owned_bases:
        database.authorize_guest(b["id"], guest_gt, ctx.author.id)
    await ctx.send(f"{member.mention} ({guest_gt}) foi autorizado em suas bases!")


@bot.command(name="alts")
@commands.has_permissions(administrator=True)
async def alts(ctx, gamertag: str):
    """Check alt accounts for a gamertag via Device ID, XUID e IP (admin only)."""
    identity = database.get_player_identity(gamertag)
    alt_list = database.find_alts(gamertag)

    embed = discord.Embed(
        title=f"🔍 Detecção de Alts: {gamertag}",
        color=discord.Color.orange() if alt_list else discord.Color.green()
    )

    if identity:
        embed.add_field(
            name="🎮 Identidade",
            value=(
                f"**XUID:** `{identity.get('xuid', 'N/A')}`\n"
                f"**Device ID:** `{identity.get('device_id', 'N/A')}`\n"
                f"**Último IP:** `{identity.get('last_ip', 'N/A')}`\n"
                f"**Visto em:** `{identity.get('last_seen', 'N/A')}`"
            ),
            inline=False
        )
    else:
        embed.description = f"Jogador `{gamertag}` não encontrado no banco de dados."
        return await ctx.send(embed=embed)

    if alt_list:
        alt_details = []
        for alt_gt in alt_list:
            alt_identity = database.get_player_identity(alt_gt)
            if alt_identity:
                is_banned = is_already_banned(alt_gt)
                status = "🚫 BANIDO" if is_banned else "✅ Limpo"
                alt_details.append(
                    f"• `{alt_gt}` — {status}\n"
                    f"  XUID: `{alt_identity.get('xuid', '?')[:12]}...`"
                )
            else:
                alt_details.append(f"• `{alt_gt}`")
        embed.add_field(
            name=f"⚠️ {len(alt_list)} Conta(s) Alternativa(s) Detectada(s)",
            value="\n".join(alt_details[:10]),
            inline=False
        )
        if len(alt_details) > 10:
            embed.set_footer(text=f"... e mais {len(alt_details) - 10} contas")
    else:
        embed.add_field(
            name="✅ Nenhuma Alt Detectada",
            value="Este jogador não compartilha Device ID, XUID ou IP com outras contas.",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name="lookup")
@commands.has_permissions(administrator=True)
async def lookup(ctx, gamertag: str):
    """Ficha completa de um jogador - identidade, Device ID, alts e infrações (admin only)."""
    identity = database.get_player_identity(gamertag)
    alt_list = database.find_alts(gamertag)

    embed = discord.Embed(
        title=f"📋 Ficha Completa: {gamertag}",
        color=discord.Color.blue()
    )

    if not identity:
        embed.description = f"Jogador `{gamertag}` não encontrado no banco de dados."
        return await ctx.send(embed=embed)

    # Seção 1: Identidade
    device_id = identity.get('device_id', 'N/A')
    if device_id and len(device_id) > 20:
        device_display = f"`{device_id[:20]}...`"
    else:
        device_display = f"`{device_id}`" if device_id else "`N/A`"

    embed.add_field(
        name="🎮 Gamertag",
        value=f"`{gamertag}`",
        inline=True
    )
    embed.add_field(
        name="🆔 Account ID (XUID)",
        value=f"`{identity.get('xuid', 'N/A')}`",
        inline=False
    )
    embed.add_field(
        name="📱 Device ID",
        value=f"`{device_id}`" if device_id else "`N/A - Aguardando conexão`",
        inline=False
    )
    embed.add_field(
        name="🕐 Último Acesso",
        value=f"`{identity.get('last_seen', 'N/A')}`",
        inline=True
    )

    # Seção 2: Status de Ban
    banned = is_already_banned(gamertag)
    embed.add_field(
        name="🚫 Status",
        value="**BANIDO**" if banned else "✅ Limpo",
        inline=True
    )

    # Seção 3: Alts
    if alt_list:
        alt_names = ", ".join([f"`{a}`" for a in alt_list[:8]])
        if len(alt_list) > 8:
            alt_names += f" ... +{len(alt_list) - 8}"
        embed.add_field(
            name=f"⚠️ {len(alt_list)} Alt(s) Detectada(s)",
            value=alt_names,
            inline=False
        )
        # Verificar se alguma alt está banida
        banned_alts = [a for a in alt_list if is_already_banned(a)]
        if banned_alts:
            embed.add_field(
                name="🚨 Alts Banidas",
                value=", ".join([f"`{a}`" for a in banned_alts]),
                inline=False
            )
    else:
        embed.add_field(
            name="👤 Alts",
            value="Nenhuma alt detectada",
            inline=False
        )

    # Seção 4: Vínculo Discord
    discord_id = database.get_discord_id_by_gamertag(gamertag)
    if discord_id:
        member = ctx.guild.get_member(int(discord_id))
        if member:
            embed.add_field(
                name="💬 Discord",
                value=f"{member.mention} (`{member.display_name}`)",
                inline=True
            )

    await ctx.send(embed=embed)


@bot.command(name="deaths", aliases=["killfeed"])
async def deaths_command(ctx):
    """Show recent kills/deaths from the server."""
    deaths = database.get_recent_deaths(10)
    if not deaths:
        return await ctx.send("Nenhum registro de morte encontrado recentemente.")
    embed = discord.Embed(
        title="Killfeed Recente - Brasil Sul", color=discord.Color.red()
    )
    for d in deaths:
        killer = d["killer_gamertag"] or "Ambiente"
        victim = d["victim_gamertag"]
        weapon = d["death_cause"] or "Desconhecido"
        dist = f"{int(d['distance'])}m" if d["distance"] else "N/A"
        loc = d["location_name"] or "Mapa"
        time_str = d["occurred_at"]
        embed.add_field(
            name=f"{killer} vs {victim}",
            value=f"Arma: `{weapon}` | Distancia: `{dist}`\nLocal: `{loc}` | Hora: `{time_str}`",
            inline=False,
        )
    embed.set_footer(text="24/7 Security System")
    await ctx.send(embed=embed)


# =============================================================================
# COMMAND: !config (configurações dinâmicas do servidor)
# =============================================================================


@bot.group(name="config", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def config_cmd(ctx):
    """Exibe e gerencia configurações dinâmicas do servidor (admin only)."""
    embed = discord.Embed(
        title="⚙️ Configurações do Servidor",
        description="Use os subcomandos abaixo para alterar as configurações.",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Horário de Raid",
        value=f"Início: `{_server_config['raid_start_hour']:02d}:00 BRT` | Fim: `{_server_config['raid_end_hour']:02d}:00 BRT`",
        inline=False,
    )
    embed.add_field(name="Limite de Fogueiras", value=f"`{_server_config['fire_limit']}` por jogador (fora da base)", inline=True)
    embed.add_field(name="Raio de Soberania", value=f"`{_server_config['base_radius']}` metros", inline=True)
    embed.add_field(
        name="Comandos disponíveis",
        value=(
            "`!config raid_start <hora>` — Muda hora de início do raid (0-23)\n"
            "`!config raid_end <hora>` — Muda hora de fim do raid (0-23)\n"
            "`!config fire_limit <n>` — Muda limite de fogueiras por jogador\n"
            "`!config base_radius <m>` — Muda raio de soberania em metros"
        ),
        inline=False,
    )
    embed.set_footer(text="Alterações entram em vigor imediatamente (sem restart).")
    await ctx.send(embed=embed)


@config_cmd.command(name="raid_start")
@commands.has_permissions(administrator=True)
async def config_raid_start(ctx, hora: int):
    """Define a hora de início do raid (BRT). Ex: !config raid_start 20"""
    if not 0 <= hora <= 23:
        return await ctx.send("❌ Hora inválida. Use um valor entre 0 e 23.")
    _server_config["raid_start_hour"] = hora
    await ctx.send(f"✅ Raid agora inicia às `{hora:02d}:00 BRT`.")
    await notify_admin_log(f"**Config alterada**: Início do raid → `{hora:02d}:00 BRT` por {ctx.author.display_name}")


@config_cmd.command(name="raid_end")
@commands.has_permissions(administrator=True)
async def config_raid_end(ctx, hora: int):
    """Define a hora de fim do raid (BRT). Ex: !config raid_end 22"""
    if not 0 <= hora <= 23:
        return await ctx.send("❌ Hora inválida. Use um valor entre 0 e 23.")
    _server_config["raid_end_hour"] = hora
    await ctx.send(f"✅ Raid agora termina às `{hora:02d}:00 BRT`.")
    await notify_admin_log(f"**Config alterada**: Fim do raid → `{hora:02d}:00 BRT` por {ctx.author.display_name}")


@config_cmd.command(name="fire_limit")
@commands.has_permissions(administrator=True)
async def config_fire_limit(ctx, limite: int):
    """Define o limite de fogueiras por jogador fora de sua base. Ex: !config fire_limit 2"""
    if not 1 <= limite <= 20:
        return await ctx.send("❌ Limite inválido. Use um valor entre 1 e 20.")
    _server_config["fire_limit"] = limite
    await ctx.send(f"✅ Limite de fogueiras por jogador fora da base: `{limite}`.")
    await notify_admin_log(f"**Config alterada**: Limite de fogueiras → `{limite}` por {ctx.author.display_name}")


@config_cmd.command(name="base_radius")
@commands.has_permissions(administrator=True)
async def config_base_radius(ctx, metros: int):
    """Define o raio de soberania das bases em metros. Ex: !config base_radius 50"""
    if not 10 <= metros <= 500:
        return await ctx.send("❌ Raio inválido. Use um valor entre 10 e 500 metros.")
    _server_config["base_radius"] = metros
    await ctx.send(f"✅ Raio de soberania de base: `{metros}` metros.")
    await notify_admin_log(f"**Config alterada**: Raio de soberania → `{metros}m` por {ctx.author.display_name}")


# =============================================================================
# ERROR HANDLER
# =============================================================================


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for common command errors."""
    if isinstance(error, commands.CommandNotFound):
        return  # Silently ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"Argumento faltando: `{error.param.name}`. Use `!help {ctx.command}` para ajuda."
        )
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Argumento invalido. Verifique o comando e tente novamente.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Voce nao tem permissao para usar este comando.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"Comando em cooldown. Tente novamente em {error.retry_after:.0f}s."
        )
    else:
        logger.error(
            f"Unhandled command error in {ctx.command}: {error}", exc_info=error
        )


# =============================================================================
# BOT STARTUP (on_ready)
# =============================================================================


@bot.event
async def on_ready():
    """Bot startup: register views, post portal/rules, start all tasks."""
    logger.info(f"Bot ready: {bot.user} (ID: {bot.user.id})")

    if not hasattr(bot, "_tasks_started"):
        bot._tasks_started = False

    # Persistent Views (so the buttons work after restart)
    bot.add_view(LeaderPortalView())
    bot.add_view(MemberPortalView())
    bot.add_view(admin_dashboard.AdminDashboardView())
    logger.info("[ON_READY] Persistent Views re-registered")

    if bot._tasks_started:
        logger.info("[ON_READY] Reconexao detectada. Tarefas ja estao rodando.")
        return

    # --- Verificar permissão MANAGE_ROLES (uma vez ao iniciar) ---
    global _can_assign_roles
    if VERIFIED_ROLE_ID:
        for guild in bot.guilds:
            me = guild.me
            if me and not me.guild_permissions.manage_roles:
                _can_assign_roles = False
                logger.warning(
                    "[ROLES] Bot sem permissão MANAGE_ROLES — atribuição do cargo "
                    "'verificado' DESATIVADA. Conceda a permissão no Discord e "
                    "coloque o cargo do bot ACIMA do cargo verificado na hierarquia."
                )
                break

    # --- Auto-setup Admin Panel ---
    for current_guild in bot.guilds:
        try:
            admin_channel = discord.utils.get(
                current_guild.text_channels, name="📱painel-admin"
            )
            if not admin_channel:
                overwrites = {
                    current_guild.default_role: discord.PermissionOverwrite(
                        read_messages=False
                    ),
                    current_guild.me: discord.PermissionOverwrite(
                        read_messages=True, send_messages=True
                    ),
                }
                admin_channel = await current_guild.create_text_channel(
                    "📱painel-admin", overwrites=overwrites
                )
                logger.info(
                    f"[ADMIN] Canal #📱painel-admin criado autonomamente na guild {current_guild.name}."
                )

            history = [msg async for msg in admin_channel.history(limit=10)]
            has_panel = any(
                msg.author == bot.user
                and msg.embeds
                and msg.embeds[0].title
                and "Painel de Administração" in msg.embeds[0].title
                and msg.embeds[0].description
                and "Vigiar Punidos" in msg.embeds[0].description
                for msg in history
            )

            if not has_panel:
                await admin_channel.purge(limit=100)

                descricao_botoes = (
                    "**📋 Guia de Funções Rápidas do Sistema:**\n\n"
                    "📊 **Status VPS** ➔ Lê uso da CPU/RAM e itens salvos no banco.\n"
                    "🚨 **Últimos Bans** ➔ Imprime os últimos 10 bans globais.\n"
                    "📍 **Radar Atual** ➔ Câmera espiã do log de ações de jogadores.\n"
                    "👥 **Clãs** ➔ Exibe pontuação e membros das 20 maiores panelas.\n\n"
                    "🔓 **Desbanir** ➔ Remove restrições e apaga rastro via FTP.\n"
                    "🕵️ **Ficha** ➔ Dossier completo criminal, clãs e alts.\n"
                    "📢 **Anúncio Global** ➔ Alerta vermelho no Discord inteiro.\n"
                    "👁️ **Vigiar Punidos** ➔ Monitora login/mortes das contas punidas.\n\n"
                    "🟢 **Toggle Free Build** ➔ Liga ou desliga restrição de construção.\n"
                    "🧲 **Forçar Sync** ➔ Reforça envios de segurança pro db-cloud.\n"
                    "🗑️ **Deletar Clã** ➔ Exclui todos os membros e panelas por nome."
                )

                embed = discord.Embed(
                    title="📱 Painel de Administração - Bot 24/7",
                    description=descricao_botoes,
                    color=discord.Color.dark_theme(),
                )
                await admin_channel.send(
                    embed=embed, view=admin_dashboard.AdminDashboardView()
                )
                logger.info("[ADMIN] Painel de botoes injetado autonomamente.")
        except Exception as e:
            logger.error(f"[ADMIN] Erro ao configurar painel mobile: {e}")

    # --- Auto-post Portal ---
    if PORTAL_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(PORTAL_CHANNEL_ID))
            if channel:
                async for message in channel.history(limit=10):
                    if message.author == bot.user:
                        await message.delete()
                # Novos embeds passo a passo (header + membro + líder)
                embed_header, embed_member, embed_leader = _build_portal_embeds()
                await channel.send(embed=embed_header)
                await channel.send(embed=embed_member, view=MemberPortalView())
                await channel.send(embed=embed_leader, view=LeaderPortalView())
                logger.info(f"Portal sent to channel {PORTAL_CHANNEL_ID}")
                try:
                    invite = await channel.create_invite(
                        max_age=0, max_uses=0, unique=False
                    )
                    logger.info(f"Invite active: {invite.url}")
                except Exception:
                    pass
                await notify_admin_log("**Bot Reiniciado**: Portal atualizado.")
            else:
                logger.warning(f"Portal channel {PORTAL_CHANNEL_ID} not found")
        except Exception as e:
            logger.error(f"Portal setup error: {e}")

    # --- Auto-post Rules ---
    if RULES_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(RULES_CHANNEL_ID))
            if channel:
                async for message in channel.history(limit=5):
                    if message.author == bot.user:
                        await message.delete()
                embed = discord.Embed(
                    title="REGRAS OFICIAIS - BRASIL SUL",
                    description=(
                        "**1. Raid Tatico Liberado**\n"
                        "Permitido aos **Sabados 20:00-22:00 (BRT)**. Radar Ativo.\n\n"
                        "**2. Construcao Militar**\n"
                        "Permitido em areas militares, bunker e litoral.\n\n"
                        "**3. Registro de Bases Automatizado**\n"
                        "Primeira parede = soberania. Invasores punidos automaticamente.\n\n"
                        "**4. Cadastro de Cla**\n"
                        "Use o canal LINK PERMANENTE para registrar perfil e cla.\n\n"
                        "**5. Kits e Clima**\n"
                        "Caminhao Kit Base nos spawns. Sem chuva, dias longos.\n\n"
                        "*Sistema justo e automatico!*"
                    ),
                    color=discord.Color.orange(),
                )
                embed.set_footer(text="Servidor 24/7 Security System")
                await channel.send(embed=embed)
                logger.info(f"Rules sent to channel {RULES_CHANNEL_ID}")
        except Exception as e:
            logger.error(f"Rules setup error: {e}")

    # --- enforce_free_building REMOVIDO - controlado pelo raid_scheduler ---

    # --- Start background tasks (MODO PAUSA) ---
    # Em modo pausa, apenas raid_scheduler, drain_ban_queue e backup_database rodam.
    # Tasks FTP (monitor_logs, sync_ban_list, ftp_health_monitor, monitor_device_ids)
    # sao iniciadas pelo raid_scheduler no sabado 20h BRT.
    logger.info("[PAUSE] ======================================")
    logger.info("[PAUSE]   BOT INICIADO EM MODO PAUSA")
    logger.info("[PAUSE]   FTP/Nitrado: DESCONECTADO")
    logger.info("[PAUSE]   Raid: Sabados 20h-22h BRT")
    logger.info("[PAUSE]   Comandos Discord: ATIVOS")
    logger.info("[PAUSE] ======================================")

    if not raid_scheduler.is_running():
        raid_scheduler.start()
        logger.info("[PAUSE] raid_scheduler ATIVO (master controller)")
    if not drain_ban_queue.is_running():
        drain_ban_queue.start()
        logger.info("[PAUSE] drain_ban_queue ATIVO")
    if not backup_database.is_running():
        backup_database.start()
        logger.info("[PAUSE] backup_database ATIVO (04:00 BRT)")

    # Tasks FTP NAO iniciadas - serao ativadas pelo raid_scheduler
    # monitor_logs, sync_ban_list, ftp_health_monitor, monitor_device_ids = PAUSADOS

    bot._tasks_started = True
    logger.info("Bot 24/7 fully operational!")


# =============================================================================
# ADMIN DASHBOARD
# =============================================================================


@bot.command(name="paineladmin")
@commands.has_permissions(administrator=True)
async def spawn_admin_dashboard(ctx):
    """Spawns the Admin Dashboard View."""
    embed = discord.Embed(
        title="📱 Painel de Administração - Bot 24/7",
        description="Selecione abaixo uma opção de gerenciamento rápido.\n*Este painel é confidencial e responde apenas aos botões.*",
        color=discord.Color.dark_theme(),
    )
    await ctx.send(embed=embed, view=admin_dashboard.AdminDashboardView())
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


# =============================================================================
# ENTRY POINT
# =============================================================================


async def main():
    async with bot:
        database.init_db()
        try:
            await bot.start(TOKEN)
        finally:
            global _persistent_ftp
            if _persistent_ftp:
                try:
                    _persistent_ftp.quit()
                except Exception:
                    pass
                _persistent_ftp = None


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shut down manually.")
