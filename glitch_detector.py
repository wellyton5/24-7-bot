import re
import logging
import auto_ban_system
from auto_ban_system import InfractionType

logger = logging.getLogger("bot247")

# Configurações
RELOG_MAX_ATTEMPTS = 4
RELOG_WINDOW_SECONDS = 300  # 5 minutos
BUILD_MIN_INTERVAL_SECONDS = 3.0
ALTITUDE_THRESHOLD = 500.0

# Emotes PERMITIDOS (animações do sistema, não são glitch)
ALLOWED_EMOTES = [
    "EmoteSitA",       # Animação de logout do DayZ
    "EmoteSitB",       # Animação de logout (variante)
    "EmoteSuicide",    # Animação de respawn (se matar)
    "VitaminBot",      # Emote de tomar polivitamínico (EmoteRPSRandom with VitaminBottle)
]

# Emotes PROIBIDOS (Glitches conhecidos no Xbox — ban imediato)
BLACKLIST_EMOTES = [
    "EmoteHeart",      # Roubo de loot através de paredes
    "EmoteSurrender",  # Atravessar paredes/portas
    "EmotePoint",      # View clipping (espiar bases)
    "EmoteWave",       # View clipping
    "EmoteLyingDown",  # Underground glitch (nome real no log: EmoteLyingDown)
    "EmoteSit",        # Solo clipping (NÃO pega SitA/SitB — filtrado pela whitelist)
]

# Estado em memória (não persistente em reinicialização do bot)
relog_history = {}  # {gamertag: [log_seconds]}
last_pos = {}  # {gamertag: {'x': x, 'z': z, 'y': y, 'time': log_seconds}}
last_kit_placed = {}  # {gamertag: log_seconds}

# Set to track already-banned XUIDs this session (avoid duplicate bans on re-read)
_banned_this_session = set()


def _parse_log_timestamp(line):
    """Extract timestamp from DayZ ADM log line (format: HH:MM:SS | ...).
    Returns seconds since midnight, or None if not parseable."""
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})\s*\|", line)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    return None


async def process_line(line):
    line = line.strip()
    if not line:
        return

    # Parse log timestamp (required for all timing-based checks)
    log_time = _parse_log_timestamp(line)

    # 1. DETECÇÃO DE EMOTES PROIBIDOS (BLACKLIST com WHITELIST)
    if "performed Emote" in line:
        # Primeiro: verificar se é um emote PERMITIDO (logout, suicide, vitamina)
        if any(allowed in line for allowed in ALLOWED_EMOTES):
            return  # Emote permitido — não banir

        # Segundo: verificar se é um emote da BLACKLIST
        detected_emote = next(
            (emote for emote in BLACKLIST_EMOTES if emote in line), None
        )

        if detected_emote:
            name_match = re.search(r'Player "(?P<name>[^"]+)"', line)
            if name_match:
                name = name_match.group("name")
                xuid_match = re.search(r"\(id=([^ )]+)", line)
                xuid = xuid_match.group(1) if xuid_match else None

                if xuid and xuid in _banned_this_session:
                    return

                reason = f"GLITCH DETECTADO: Uso de emote proibido ({detected_emote}) para clipping/exploit."
                logger.warning(
                    f"[SECURITY] Banindo {name} por Emote Proibido: {detected_emote}"
                )

                await auto_ban_system.ban_player_immediate_async(
                    gamertag=name,
                    xuid=None,
                    reason=reason,
                    infraction_type=InfractionType.GLITCH_ABUSE,
                    evidence=line,
                )

                if xuid:
                    _banned_this_session.add(xuid)
                return

    # Skip all timing-based checks if we can't parse log timestamp
    if log_time is None:
        return

    # 2. RELOG / LAG ABUSE
    if (
        "connected" in line.lower()
        and "player" in line.strip().lower()
        and "is connected" not in line.lower()
    ):
        name_match = re.search(r'Player "(?P<name>[^"]+)"', line)
        if name_match:
            name = name_match.group("name")
            if name not in relog_history:
                relog_history[name] = []

            # Limpar histórico antigo (usando timestamp do log)
            relog_history[name] = [
                t
                for t in relog_history[name]
                if log_time - t < RELOG_WINDOW_SECONDS and log_time >= t
            ]
            relog_history[name].append(log_time)

            if len(relog_history[name]) >= RELOG_MAX_ATTEMPTS:
                xuid_match = re.search(r"\(id=([^ )]+)", line)
                xuid = xuid_match.group(1) if xuid_match else None
                if xuid and xuid in _banned_this_session:
                    return
                reason = (
                    f"Abuso de Relog/Lag: {len(relog_history[name])} conexões em 5 min"
                )
                logger.warning(f"[SECURITY] Banindo {name} por Relog Abuse.")
                await auto_ban_system.ban_player_immediate_async(
                    gamertag=name,
                    xuid=None,
                    reason=reason,
                    infraction_type=InfractionType.GLITCH_ABUSE,
                    evidence=f"Histórico: {relog_history[name]}",
                )
                if xuid:
                    _banned_this_session.add(xuid)
                return

    # 3. FLY HACK / AIR SWIMMING e 4. CONSTRUÇÃO RÁPIDA
    pattern = r'Player "(?P<name>[^"]+)" \(id=(?P<xuid>[^ )]+) pos=<(?P<coords>[^>]+)>\)(?P<action>.+)'
    match = re.search(pattern, line)

    if match:
        name = match.group("name")
        xuid = match.group("xuid")
        coords_str = match.group("coords")
        action = match.group("action")

        # Skip if already banned this session
        if xuid in _banned_this_session:
            return

        try:
            # DayZ ADM format: <X, Z_map, Y_height> where THIRD value is height
            parts = coords_str.split(",")
            x, z, y = float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            return

        # --- Verificação de Altitude ---
        if y > ALTITUDE_THRESHOLD:
            reason = f"Altitude Proibida: Detectado a {y}m. (SKY BASE / FLY HACK)"
            await auto_ban_system.ban_player_immediate_async(
                name, None, reason, InfractionType.SKY_BASE, line
            )
            _banned_this_session.add(xuid)
            return

        # --- Verificação de Fly Hack (Subida Vertical) ---
        if name in last_pos:
            prev = last_pos[name]
            time_diff = log_time - prev["time"]
            if 0 < time_diff < 10:  # Check short intervals
                y_diff = y - prev["y"]
                dist_xz = ((x - prev["x"]) ** 2 + (z - prev["z"]) ** 2) ** 0.5

                # Se subir > 5 metros quase sem se mover pro lado
                if y_diff > 5.0 and dist_xz < 1.0:
                    reason = f"Fly Hack / Air Swimming: Subida vertical de {y_diff:.1f}m detectada."
                    await auto_ban_system.ban_player_immediate_async(
                        name, None, reason, InfractionType.FLY_HACK, line
                    )
                    _banned_this_session.add(xuid)
                    return

        last_pos[name] = {"x": x, "z": z, "y": y, "time": log_time}

        # --- Verificação de Construção Rápida ---
        if "placed" in action and (
            "Kit" in action or "Fence" in action or "Watchtower" in action
        ):
            last_kit_placed[name] = log_time

        if "Built" in action:
            if name in last_kit_placed:
                build_time = log_time - last_kit_placed[name]
                if 0 < build_time < BUILD_MIN_INTERVAL_SECONDS:
                    reason = f"Construção Glitched/Rápida: {action.strip()} em {build_time:.1f}s após o kit."
                    await auto_ban_system.ban_player_immediate_async(
                        name, None, reason, InfractionType.LAG_MACHINE, line
                    )
                    _banned_this_session.add(xuid)
                    return
