# -*- coding: utf-8 -*-
"""
Database Module - Bot 24/7 Security System
SQLite database for clans, bases, identities, and security logs.
"""

import functools
import logging
import math
import os
import sqlite3
import time
from datetime import datetime

logger = logging.getLogger("bot247")


def retry_db(max_retries=5, delay=1.0):
    """Decorador padrão para auto-recuperar funções de banco travadas.

    IMPORTANTE: As funções decoradas DEVEM usar try/finally para fechar conn,
    pois o retry recria a conexão a cada tentativa.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_error = e
                    if (
                        "database is locked" in str(e).lower()
                        and attempt < max_retries - 1
                    ):
                        logger.warning(
                            f"[DB] Lock em '{func.__name__}'. Retentando ({attempt + 1}/{max_retries})..."
                        )
                        time.sleep(delay)
                        continue
                    raise
            raise last_error  # Se esgotou tentativas

        return wrapper

    return decorator


# Configurações do Banco de Dados
SEC_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.db")
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bigode_unified.db")

BASE_RADIUS = int(os.getenv("BASE_RADIUS", 50))


def _get_conn(db_path=None):
    """Retorna conexão otimizada para alta concorrência."""
    # timeout=30.0 faz o banco aguardar liberação em vez de travar sob estresse
    conn = sqlite3.connect(db_path or SEC_DB, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")  # Escrita e leitura simultâneas
    conn.execute("PRAGMA synchronous=NORMAL")  # Performance acelerada
    conn.execute("PRAGMA cache_size=-64000")  # Usa até 64MB de RAM para cache
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Inicializa todas as tabelas e índices."""
    conn = _get_conn()
    try:
        _init_db_tables(conn)
    finally:
        conn.close()
    logger.info("[DB] Banco de dados inicializado com sucesso")


def _init_db_tables(conn):
    """Cria tabelas e índices (chamado por init_db)."""
    cur = conn.cursor()

    # [TABELA] Vínculos Discord-Xbox
    cur.execute("""
        CREATE TABLE IF NOT EXISTS discord_links_247 (
            discord_id TEXT PRIMARY KEY,
            gamertag TEXT NOT NULL UNIQUE,
            linked_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # [TABELA] Clãs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clans_247 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            leader_discord_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # [TABELA] Membros de Clã
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_members_247 (
            clan_id INTEGER,
            discord_id TEXT NOT NULL,
            gamertag TEXT,
            role TEXT DEFAULT 'member',
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (clan_id, discord_id),
            FOREIGN KEY (clan_id) REFERENCES clans_247(id) ON DELETE CASCADE
        )
    """)

    # [TABELA] Convites de Clã
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clan_invites_247 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan_id INTEGER,
            discord_id TEXT NOT NULL,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(clan_id, discord_id),
            FOREIGN KEY (clan_id) REFERENCES clans_247(id) ON DELETE CASCADE
        )
    """)

    # [TABELA] Infrações e Muro da Vergonha
    # Schema compatível com auto_ban_system.py (inclui todos os campos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS infractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gamertag TEXT NOT NULL,
            discord_id TEXT,
            xuid TEXT,
            ip_address TEXT,
            infraction_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'CRÍTICA',
            description TEXT,
            evidence TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto_banned BOOLEAN DEFAULT 1,
            ban_lifted BOOLEAN DEFAULT 0,
            admin_notes TEXT
        )
    """)
    # Migração: adicionar colunas faltantes em bancos existentes
    for col_sql in [
        "ALTER TABLE infractions ADD COLUMN discord_id TEXT",
        "ALTER TABLE infractions ADD COLUMN ip_address TEXT",
        "ALTER TABLE infractions ADD COLUMN severity TEXT NOT NULL DEFAULT 'CRÍTICA'",
        "ALTER TABLE infractions ADD COLUMN detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE infractions ADD COLUMN auto_banned BOOLEAN DEFAULT 1",
        "ALTER TABLE infractions ADD COLUMN ban_lifted BOOLEAN DEFAULT 0",
        "ALTER TABLE infractions ADD COLUMN admin_notes TEXT",
    ]:
        try:
            cur.execute(col_sql)
        except sqlite3.OperationalError:
            pass  # Coluna já existe

    # [TABELA] Identidade de Jogador (AltDetector)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_identities (
            gamertag TEXT PRIMARY KEY,
            xuid TEXT,
            last_ip TEXT,
            device_id TEXT,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # [TABELA] Auditoria de Conexões
    cur.execute("""
        CREATE TABLE IF NOT EXISTS security_logs_247 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gamertag TEXT NOT NULL,
            ip_address TEXT,
            xuid TEXT,
            device_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # [TABELA] Logouts Recentes (AltDetector por Proximidade)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recent_logouts (
            gamertag TEXT PRIMARY KEY,
            x FLOAT NOT NULL,
            z FLOAT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # [TABELA] Bases Registradas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bases_security (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_gamertag TEXT NOT NULL,
            x FLOAT NOT NULL,
            z FLOAT NOT NULL,
            owner_discord_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # [TABELA] Incidentes de Raid (Radar)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raid_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id INTEGER,
            attacker_gamertag TEXT,
            incident_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (base_id) REFERENCES bases_security(id)
        )
    """)

    # [TABELA] Permissões Extras de Base
    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_permissions (
            base_id INTEGER,
            gamertag_authorized TEXT,
            authorized_by TEXT,
            PRIMARY KEY (base_id, gamertag_authorized),
            FOREIGN KEY (base_id) REFERENCES bases_security(id)
        )
    """)

    # [TABELA] Limites de Itens (Spam Filter)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS item_limits (
            gamertag TEXT,
            item_type TEXT,
            count INTEGER DEFAULT 0,
            last_updated DATETIME,
            PRIMARY KEY (gamertag, item_type)
        )
    """)

    # [TABELA] Monitoramento Interno
    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_health_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            auto_fixed BOOLEAN DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            resolved BOOLEAN DEFAULT 0,
            resolved_time TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_auto_fixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fix_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            problem_type TEXT NOT NULL,
            fix_action TEXT NOT NULL,
            success BOOLEAN DEFAULT 1,
            details TEXT
        )
    """)

    # --- TRIGGERS AUTÔNOMOS ---
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS auto_cleanup_health_logs
        AFTER INSERT ON db_health_checks
        WHEN (SELECT COUNT(*) FROM db_health_checks) > 5000
        BEGIN
            DELETE FROM db_health_checks WHERE id IN (
                SELECT id FROM db_health_checks ORDER BY check_time ASC LIMIT 500
            );
        END;
    """)

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_health_checks_time ON db_health_checks(check_time)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_links_gamertag ON discord_links_247(gamertag)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_clan_members_clan ON clan_members_247(clan_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_clan_members_gt ON clan_members_247(gamertag)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_infractions_gt ON infractions(gamertag)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_infractions_xuid ON infractions(xuid)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_security_logs_gt ON security_logs_247(gamertag)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_security_logs_ts ON security_logs_247(timestamp)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_bases_owner ON bases_security(owner_gamertag)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_identities_xuid ON player_identities(xuid)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_identities_ip ON player_identities(last_ip)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_raid_base ON raid_incidents(base_id)")

    conn.commit()


# --- VÍNCULOS ---


@retry_db()
def create_discord_link_247(discord_id, gamertag):
    """Vincula um ID do Discord a uma Gamertag do Xbox."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO discord_links_247 (discord_id, gamertag) VALUES (?, ?)",
            (str(discord_id), gamertag),
        )
        conn.commit()
    finally:
        conn.close()


def unlink_gamertag(discord_id):
    """Remove o vínculo da Gamertag e registros de clã de um usuário."""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM clans_247 WHERE leader_discord_id = ?", (str(discord_id),)
        )
        clan_led = cur.fetchone()
        cur.execute(
            "DELETE FROM discord_links_247 WHERE discord_id = ?", (str(discord_id),)
        )
        cur.execute(
            "DELETE FROM clan_members_247 WHERE discord_id = ?", (str(discord_id),)
        )
        if clan_led:
            clan_id = clan_led[0]
            cur.execute("DELETE FROM clan_invites_247 WHERE clan_id = ?", (clan_id,))
            cur.execute("DELETE FROM clan_members_247 WHERE clan_id = ?", (clan_id,))
            cur.execute("DELETE FROM clans_247 WHERE id = ?", (clan_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Erro ao desvincular: {e}")
        return False
    finally:
        conn.close()


def get_gamertag_by_discord(discord_id):
    """Busca a gamertag vinculada ao Discord ID (Vínculo direto ou Clã)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT gamertag FROM discord_links_247 WHERE discord_id = ?",
        (str(discord_id),),
    )
    row = cur.fetchone()
    if row:
        conn.close()
        return row[0]
    cur.execute(
        "SELECT gamertag FROM clan_members_247 WHERE discord_id = ? AND gamertag IS NOT NULL",
        (str(discord_id),),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_discord_id_by_gamertag(gamertag):
    """Busca o Discord ID vinculado a uma gamertag."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT discord_id FROM discord_links_247 WHERE gamertag = ?",
        (gamertag,),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def update_gamertag_link(discord_id, new_gamertag):
    """Atualiza a gamertag de um vínculo existente."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE discord_links_247 SET gamertag = ? WHERE discord_id = ?",
        (new_gamertag, str(discord_id)),
    )
    conn.commit()
    conn.close()


# --- BASES ---


@retry_db()
def register_base(gamertag, x, z, discord_id=None):
    """Registra uma nova base com soberania."""
    if not discord_id:
        discord_id = get_discord_id_by_gamertag(gamertag)
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO bases_security (owner_gamertag, x, z, owner_discord_id) VALUES (?, ?, ?, ?)",
            (gamertag, x, z, str(discord_id) if discord_id else None),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info(f"[DB] Base registrada: {gamertag} em [{int(x)}, {int(z)}]")


# Alias para compatibilidade
register_new_base = register_base


def get_bases():
    """Retorna todas as bases registradas como tuples."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT owner_gamertag, x, z, owner_discord_id, id FROM bases_security")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_security_bases():
    """Retorna todas as bases como lista de dicts (para uso no parser de logs)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, owner_gamertag, x, z, owner_discord_id FROM bases_security")
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "owner": r[1],
            "x": r[2],
            "z": r[3],
            "owner_discord_id": r[4],
            "radius": BASE_RADIUS,
        }
        for r in rows
    ]


def get_base_at(x, z, radius=None):
    """Verifica se existe uma base nas coordenadas e retorna dict do dono."""
    r = radius or BASE_RADIUS
    bases = get_security_bases()
    for base in bases:
        distance = math.sqrt((x - base["x"]) ** 2 + (z - base["z"]) ** 2)
        if distance <= r:
            return base
    return None


# Alias para compatibilidade
find_nearest_base = get_base_at


@retry_db()
def update_base_owner_discord(base_id, discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE bases_security SET owner_discord_id = ? WHERE id = ?",
        (str(discord_id), base_id),
    )
    conn.commit()
    conn.close()


@retry_db()
def add_raid_incident(base_id, attacker_gamertag):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO raid_incidents (base_id, attacker_gamertag) VALUES (?, ?)",
        (base_id, attacker_gamertag),
    )
    conn.commit()
    conn.close()


def count_recent_incidents(base_id, minutes=5):
    """Conta incidentes recentes em uma base (SQL injection corrigida)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM raid_incidents WHERE base_id = ? AND incident_time > datetime('now', '-' || ? || ' minutes')",
        (base_id, minutes),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


@retry_db()
def authorize_guest(base_id, gamertag_guest, authorized_by_discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO base_permissions (base_id, gamertag_authorized, authorized_by) VALUES (?, ?, ?)",
        (base_id, gamertag_guest, str(authorized_by_discord_id)),
    )
    conn.commit()
    conn.close()


def revoke_guest(base_id, gamertag_guest):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM base_permissions WHERE base_id = ? AND gamertag_authorized = ?",
        (base_id, gamertag_guest),
    )
    conn.commit()
    conn.close()


def get_base_permissions(base_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT gamertag_authorized FROM base_permissions WHERE base_id = ?", (base_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


# --- CLÃS ---


@retry_db()
def create_clan_247(name, leader_discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO clans_247 (name, leader_discord_id) VALUES (?, ?)",
            (name, str(leader_discord_id)),
        )
        clan_id = cur.lastrowid
        conn.commit()
        return clan_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


@retry_db()
def delete_clan_by_leader(leader_discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        # Primeiro, buscar o ID do clã
        cur.execute(
            "SELECT id FROM clans_247 WHERE leader_discord_id = ?",
            (str(leader_discord_id),),
        )
        row = cur.fetchone()
        if not row:
            return False

        clan_id = row[0]

        # 1. Deletar todos os membros associados ao clã
        cur.execute("DELETE FROM clan_members_247 WHERE clan_id = ?", (clan_id,))

        # 2. Deletar todos os convites pendentes associados ao clã
        cur.execute("DELETE FROM clan_invites_247 WHERE clan_id = ?", (clan_id,))

        # 3. Deletar o registro do clã
        cur.execute("DELETE FROM clans_247 WHERE id = ?", (clan_id,))

        conn.commit()
        logger.info(
            f"[DB] Clã {clan_id} e todos os registros relacionados foram deletados."
        )
        return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Erro ao deletar clã e registros: {e}")
        return False
    finally:
        conn.close()


def get_clan_by_leader(discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name FROM clans_247 WHERE leader_discord_id = ?", (str(discord_id),)
    )
    row = cur.fetchone()
    conn.close()
    return {"id": row[0], "name": row[1]} if row else None


def get_clan_id_by_member(discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT clan_id FROM clan_members_247 WHERE discord_id = ?", (str(discord_id),)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


@retry_db()
def add_clan_member(clan_id, discord_id, gamertag=None):
    conn = _get_conn()
    cur = conn.cursor()
    safe_discord_id = str(discord_id) if discord_id else "0"
    cur.execute(
        "INSERT OR REPLACE INTO clan_members_247 (clan_id, discord_id, gamertag) VALUES (?, ?, ?)",
        (clan_id, safe_discord_id, gamertag),
    )
    conn.commit()
    conn.close()


@retry_db()
def remove_clan_member(clan_id, discord_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM clan_members_247 WHERE clan_id = ? AND discord_id = ?",
        (clan_id, str(discord_id)),
    )
    conn.commit()
    conn.close()


def get_clan_members_gamertags(clan_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT gamertag FROM clan_members_247 WHERE clan_id = ? AND gamertag IS NOT NULL",
        (clan_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_clans():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, leader_discord_id FROM clans_247")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "leader": r[2]} for r in rows]


def get_pending_clan_by_gamertag(gamertag):
    """Busca se um gamertag foi pré-adicionado a um clã mas não tem Discord vinculado."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT clan_id FROM clan_members_247 WHERE gamertag = ? AND (discord_id = '0' OR discord_id = 'None')",
        (gamertag,),
    )
    row = cur.fetchone()
    conn.close()
    return row if row else None


# --- CONVITES ---


@retry_db()
def create_clan_invite(clan_id, gamertag):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO clan_invites_247 (clan_id, discord_id) VALUES (?, ?)",
            (clan_id, str(gamertag)),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Erro ao criar convite: {e}")
        return False
    finally:
        conn.close()


def get_pending_invites(gamertag):
    """Retorna convites pendentes com clan_id incluído."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT ci.id, ci.clan_id, c.name FROM clan_invites_247 ci JOIN clans_247 c ON ci.clan_id = c.id WHERE ci.discord_id COLLATE NOCASE = ?",
        (str(gamertag),),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "clan_id": r[1], "clan_name": r[2]} for r in rows]


@retry_db()
def delete_invite(invite_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM clan_invites_247 WHERE id = ?", (invite_id,))
    conn.commit()
    conn.close()


def get_invite_by_id(invite_id):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT clan_id, discord_id FROM clan_invites_247 WHERE id = ?", (invite_id,)
    )
    row = cur.fetchone()
    conn.close()
    return {"clan_id": row[0], "discord_id": row[1]} if row else None


# --- LOGS & SECURITY ---


def log_connection(gamertag, ip, xuid, device_id=None):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO security_logs_247 (gamertag, ip_address, xuid, device_id) VALUES (?, ?, ?, ?)",
            (gamertag, ip, xuid, device_id),
        )
        conn.commit()
    finally:
        conn.close()
    update_player_identity(gamertag, xuid, ip, device_id)


def update_player_identity(gamertag, xuid, ip=None, device_id=None):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO player_identities (gamertag, xuid, last_ip, device_id, last_seen)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(gamertag) DO UPDATE SET
                xuid = COALESCE(excluded.xuid, xuid),
                last_ip = COALESCE(excluded.last_ip, last_ip),
                device_id = COALESCE(excluded.device_id, device_id),
                last_seen = datetime('now')
        """,
            (gamertag, xuid, ip, device_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_player_identity(gamertag):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT gamertag, xuid, last_ip, device_id, last_seen FROM player_identities WHERE gamertag = ?",
        (gamertag,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "gamertag": row[0],
            "xuid": row[1],
            "last_ip": row[2],
            "device_id": row[3],
            "last_seen": row[4],
        }
    return None


def get_player_identity_by_xuid(xuid):
    """Retorna identidade de um jogador pelo XUID."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT gamertag, xuid, last_ip, device_id, last_seen FROM player_identities WHERE xuid = ?",
        (xuid,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "gamertag": row[0],
            "xuid": row[1],
            "last_ip": row[2],
            "device_id": row[3],
            "last_seen": row[4],
        }
    return None


def get_player_id(gamertag):
    """Retorna o XUID de um jogador pelo gamertag."""
    identity = get_player_identity(gamertag)
    return identity["xuid"] if identity else None


def find_alts(gamertag):
    identity = get_player_identity(gamertag)
    if not identity:
        return []
    conn = _get_conn()
    cur = conn.cursor()
    alts = set()
    if identity["xuid"]:
        cur.execute(
            "SELECT gamertag FROM player_identities WHERE xuid = ? AND gamertag != ?",
            (identity["xuid"], gamertag),
        )
        for row in cur.fetchall():
            alts.add(row[0])
    if identity["last_ip"]:
        cur.execute(
            "SELECT gamertag FROM player_identities WHERE last_ip = ? AND gamertag != ?",
            (identity["last_ip"], gamertag),
        )
        for row in cur.fetchall():
            alts.add(row[0])
    if identity["device_id"]:
        cur.execute(
            "SELECT gamertag FROM player_identities WHERE device_id = ? AND gamertag != ?",
            (identity["device_id"], gamertag),
        )
        for row in cur.fetchall():
            alts.add(row[0])
    conn.close()
    return list(alts)


# --- ALT DETECTOR DE PROXIMIDADE ---


def log_player_logout(gamertag, x, z):
    """Registra a última posição conhecida de um jogador ao deslogar."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO recent_logouts (gamertag, x, z, timestamp) VALUES (?, ?, ?, ?) ",
        (gamertag, x, z, datetime.now()),
    )
    conn.commit()
    conn.close()


def check_proximity_alt(new_gamertag, x, z, time_window_seconds=120):
    """
    Verifica se alguém deslogou muito perto (5m) nas últimas janelas de tempo.
    Retorna a gamertag do possível 'Original' se encontrado.
    """
    conn = _get_conn()
    cur = conn.cursor()
    # Limpa logouts muito velhos para manter performance (> 1 hora)
    cur.execute(
        "DELETE FROM recent_logouts WHERE timestamp < datetime('now', '-1 hour')"
    )
    conn.commit()

    # Busca logouts recentes (últimos N segundos) num raio de 5 metros
    # Nota: Usamos aproximação quadrada simples para performance, depois math se necessário
    cur.execute(
        """
        SELECT gamertag, x, z FROM recent_logouts
        WHERE gamertag != ?
        AND timestamp > datetime('now', '-' || ? || ' seconds')
        AND x BETWEEN ? AND ?
        AND z BETWEEN ? AND ?
    """,
        (
            new_gamertag,
            time_window_seconds,
            x - 5.0,
            x + 5.0,
            z - 5.0,
            z + 5.0,
        ),
    )

    rows = cur.fetchall()
    conn.close()

    for row in rows:
        prev_gt, prev_x, prev_z = row
        dist = math.sqrt((x - prev_x) ** 2 + (z - prev_z) ** 2)
        if dist <= 5.0:
            return prev_gt

    return None


# --- ITEMS & LIMITS ---


def get_item_count(gamertag, item_type):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT count FROM item_limits WHERE gamertag = ? AND item_type = ?",
        (gamertag, item_type),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def increment_item_count(gamertag, item_type):
    conn = _get_conn()
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
    conn.close()


# --- PVP EVENTS ---


def add_event(event_type, x, y, z, weapon, killer, victim, distance, timestamp):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events (event_type, game_x, game_y, game_z, weapon, killer_name, victim_name, distance, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (event_type, x, y, z, weapon, killer, victim, distance, timestamp),
    )
    conn.commit()
    conn.close()


def get_recent_deaths(limit=10):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT killer_gamertag, victim_gamertag, death_cause, distance, location_name, occurred_at FROM deaths_log ORDER BY occurred_at DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return rows
    except sqlite3.OperationalError:
        conn.close()
        return []


# --- AUTONOMIA & SAÚDE ---


def check_db_health():
    """Realiza um check-up autônomo no banco de dados."""
    try:
        conn = _get_conn()
        cur = conn.cursor()

        # 1. Integridade SQLite
        cur.execute("PRAGMA integrity_check")
        integrity = cur.fetchone()[0]

        # 2. Tamanho das tabelas críticas
        cur.execute("SELECT COUNT(*) FROM security_logs_247")
        log_count = cur.fetchone()[0]

        status = "OK" if integrity == "ok" else "ERROR"
        details = f"Integridade: {integrity} | Logs: {log_count}"

        cur.execute(
            "INSERT INTO db_health_checks (check_type, status, details) VALUES (?, ?, ?)",
            ("health_check", status, details),
        )

        # Logica de auto-fix se logs estiverem pesados (> 50k)
        if log_count > 50000:
            auto_fix_db("high_log_volume")

        conn.commit()
        conn.close()
        return status == "OK"
    except Exception as e:
        logger.error(f"[DB] Falha no Health Check: {e}")
        return False


def auto_fix_db(problem_type):
    """Executa correções automáticas sem intervenção humana."""
    conn = _get_conn()
    try:
        cur = conn.cursor()

        if problem_type == "high_log_volume":
            # Limpa logs antigos deixando os últimos 10k
            cur.execute("""
                DELETE FROM security_logs_247
                WHERE id NOT IN (SELECT id FROM security_logs_247 ORDER BY timestamp DESC LIMIT 10000)
            """)
            cur.execute("VACUUM")

            cur.execute(
                "INSERT INTO db_auto_fixes (problem_type, fix_action, details) VALUES (?, ?, ?)",
                (
                    "high_log_volume",
                    "cleanup_and_vacuum",
                    "Reduzido volume de logs para 10k e executado VACUUM",
                ),
            )
            logger.info("[DB] Auto-fix executado: Limpeza de logs e otimização")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("[DB] Banco de dados criado/verificado com sucesso.")
