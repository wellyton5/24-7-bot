import io
import json
import math
import os
import re
from dotenv import load_dotenv
import discord
from discord import ui
from discord.ext import tasks, commands
from datetime import datetime, timedelta, timezone
import requests

# Importar auxiliares locais
import database
from ftp_helpers import connect_ftp, download_file, upload_file

load_dotenv()

# Configurações do Bot
TOKEN = os.getenv("DISCORD_TOKEN")
BAN_CHANNEL_ID = os.getenv("BAN_CHANNEL")
BASE_RADIUS = os.getenv("BASE_RADIUS", 50)  # Raio de proteção da base em metros
STATE_FILE = "bot_state.json"
GAMEPLAY_CONFIG_PATH = "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json"
LOCAL_GAMEPLAY_CONFIG = "cfggameplay_temp.json"
VERIFIED_ROLE_ID = os.getenv("VERIFIED_ROLE_ID")
PORTAL_CHANNEL_ID = os.getenv("PORTAL_CHANNEL_ID")
RADAR_WEBHOOK_URL = os.getenv("RADAR_WEBHOOK_URL")
RULES_CHANNEL_ID = os.getenv("RULES_CHANNEL_ID", "1384330092586729472")
TRUCK_ALERTS_CHANNEL_ID = os.getenv("TRUCK_ALERTS_CHANNEL_ID", "1384330076174155867")

# Lista de Spawns Oficiais de Caminhão Kit (Extraído do cfgeventspawns.xml)
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

# Estado global para caminhões
active_truck_timers = {}  # {(x, z): {"expiry": datetime, "player": str, "warning_sent": bool}}
last_available_trucks = set()  # {(x, z), ...}

# Configurações Nitrado (para Restart)
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command(name="regras")
async def regras(ctx):
    """Exibe as regras oficiais do servidor Brasil Sul."""
    embed = discord.Embed(
        title="📜 REGRAS OFICIAIS - BRASIL SUL",
        description=(
            "**1. Raid Tático Liberado** ⚔️\n"
            "O Raid é permitido apenas aos **Sábados das 20:00 às 22:00 (BRT)**. "
            "Rams e invasões técnicas são permitidas pois o servidor possui **Radar Ativo**.\n\n"
            "**2. Construção Militar** 🏗️\n"
            "É permitido construir em áreas militares, inclusive no bunker e áreas do litoral.\n\n"
            "**3. Registro de Bases Automatizado** 🛡️\n"
            "A partir do momento que você **constrói sua primeira parede**, o sistema registra a soberania. "
            "Apenas o seu perfil (e seu clã cadastrado) poderá construir ou mover itens (barracas, baús, tendas, fogueiras, etc) na área. "
            "Invasores tentando construir ou fazer glitch serão **punidos automaticamente**.\n\n"
            "**4. Cadastro de Clã (IMPORTANTE)** 🔗\n"
            "Use o canal **🔗 LINK PERMANENTE** para registrar seu perfil, seu clã e gerenciar seus membros. "
            "Isso garante que seus amigos não sejam banidos por engano na sua base.\n\n"
            "**5. Kits e Clima** 🚚☀️\n"
            "• Caminhão Kit Base espalhado em locais de spawn.\n"
            "• Sem chuva, noites curtas e dias longos.\n\n"
            "*Sem mimimi e sem choro. O sistema é justo e automático!*"
        ),
        color=discord.Color.orange(),
    )
    embed.set_footer(text="Servidor 24/7 Security System")
    await ctx.send(embed=embed)


# Estado global para tailing
current_log_file = ""
last_byte_offset = 0


def _is_garden(item_name):
    """Verifica se o item é um tipo de garden/plantação."""
    garden_keywords = [
        "garden",
        "greenhouse",
        "planting",
        "vegetable",
        "plot",
        "farming",
    ]
    item_lower = item_name.lower()
    return any(keyword in item_lower for keyword in garden_keywords)


def _is_fireplace(item_name):
    """Verifica se o item é um tipo de fireplace/fogueira."""
    fireplace_keywords = ["fireplace", "oven", "stove", "campfire", "fire"]
    item_lower = item_name.lower()

    # Verificação especial para barrel with holes
    if "barrel" in item_lower and "hole" in item_lower:
        return True

    return any(keyword in item_lower for keyword in fireplace_keywords)


def _is_garden_or_fireplace(item_name):
    """Verifica se o item é garden OU fireplace."""
    return _is_garden(item_name) or _is_fireplace(item_name)


async def enforce_free_building():
    """Garante que a construção livre esteja ativada no cfggameplay.json"""
    print("[CONFIG] Verificando modo de construcao livre...")
    if download_file(GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG):
        try:
            with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
                config = json.load(f)

            modified = False
            hologram_data = config.get("BaseBuildingData", {}).get("HologramData", {})

            # Lista de chaves que devem ser 'true' para construção livre total
            keys_to_fix = [
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

            for key in keys_to_fix:
                if hologram_data.get(key) is not True:
                    hologram_data[key] = True
                    modified = True

            if modified:
                print("[CONFIG] Restricoes detectadas! Forcando construcao livre...")
                with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
                    json.dump(config, f, indent=4)

                if upload_file(LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH):
                    msg = "🛠️ **CONFIGURAÇÃO ALTERADA**\nO modo de **Construção Livre** foi forçado pelo bot. O servidor precisa ser reiniciado para aplicar!"
                    await notify_ban(msg)
                    print("[CONFIG] cfggameplay.json atualizado no servidor.")
            else:
                print("[CONFIG] Construcao livre ja esta 100% ativa.")

        except Exception as e:
            print(f"Erro ao processar JSON: {e}")
        finally:
            if os.path.exists(LOCAL_GAMEPLAY_CONFIG):
                os.remove(LOCAL_GAMEPLAY_CONFIG)
    else:
        print("[CONFIG] Nao foi possivel baixar o cfggameplay.json para verificar.")


class ClanPortalView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # View persistente

    @ui.button(
        label="🔗 Vincular Gamertag",
        style=discord.ButtonStyle.blurple,
        custom_id="portal:link_gamertag",
    )
    async def link_gamertag(self, interaction: discord.Interaction, button: ui.Button):
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
                "❌ Vincule sua Gamertag primeiro!", ephemeral=True
            )
        await interaction.response.send_modal(CreateClanModal())

    @ui.button(
        label="➕ Adicionar Membro",
        style=discord.ButtonStyle.primary,
        custom_id="portal:add_member",
    )
    async def add_member(self, interaction: discord.Interaction, button: ui.Button):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "❌ Você precisa ser líder de um clã para adicionar membros!",
                ephemeral=True,
            )
        await interaction.response.send_modal(AddMemberModal())

    @ui.button(
        label="🗑️ CANCELAR REGISTROS",
        style=discord.ButtonStyle.danger,
        custom_id="portal:dissolve_clan",
    )
    async def dissolve_clan(self, interaction: discord.Interaction, button: ui.Button):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "❌ Apenas líderes de clã podem acessar esta opção.", ephemeral=True
            )
        await interaction.response.send_modal(DissolveClanModal())


async def restart_nitrado():
    """Chama a API da Nitrado para reiniciar o servidor."""
    if not NITRADO_TOKEN or not SERVICE_ID:
        print("[NITRADO] Erro: Credenciais ausentes no .env")
        return False

    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}

    try:
        response = requests.post(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("[NITRADO] Comando de restart enviado com sucesso!")
            return True
        else:
            print(
                f"[NITRADO] Erro no restart: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"[NITRADO] Erro de conexao: {e}")
        return False


@bot.command(name="portal")
@commands.has_permissions(administrator=True)
async def portal_setup(ctx):
    """Configura o portal interativo de clãs."""
    embed = discord.Embed(
        title="🏆 Portal de Clãs - Brasil Sul",
        description=(
            "Centralize sua gestão aqui!\n\n"
            "**1.** Use o botão azul para vincular seu Xbox.\n"
            "**2.** Use o botão verde para registrar seu clã.\n"
            "**3.** Use o botão azul (Adicionar) para cadastrar os Gamertags de seus amigos no seu clã.\n"
            "**4.** Use o botão cinza para aceitar convites pendentes.\n"
            "**5.** Use o botão vermelho para **CANCELAR REGISTROS** e apagar seu clã atual.\n\n"
            "*Ação de líder: Ao adicionar um membro, ele é liberado automaticamente no Radar da sua base.*"
        ),
        color=discord.Color.gold(),
    )
    await ctx.send(embed=embed, view=ClanPortalView())
    await ctx.message.delete()


@tasks.loop(seconds=60)
async def raid_scheduler():
    """Agendador para desativar o Raid aos Sabados as 22:00 BRT."""
    # Horário de Brasília (UTC-3)
    br_now = datetime.now(timezone.utc) - timedelta(hours=3)

    # Sábado = 5 (0: Seg, ..., 5: Sab, 6: Dom)
    if br_now.weekday() == 5:
        if br_now.hour == 22 and br_now.minute == 0:
            print("[RAID] HORA DE ENCERRAR O RAID! Ajustando configuracoes...")

            # 1. Desativar Dano em Base no cfggameplay.json
            if download_file(GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG):
                try:
                    with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
                        config = json.load(f)

                    if (
                        config.get("GeneralData", {}).get("disableBaseDamage")
                        is not True
                    ):
                        config["GeneralData"]["disableBaseDamage"] = True

                        with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
                            json.dump(config, f, indent=4)

                        if upload_file(LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH):
                            print("[RAID] JSON atualizado. Reiniciando servidor...")

                            # 2. Reiniciar Servidor
                            if await restart_nitrado():
                                msg = "🛑 **FIM DO RAID (AGENDADO)**\nO Raid foi encerrado automaticamente. Dano em bases desativado e servidor reiniciando!"
                                await notify_ban(msg)
                except Exception as e:
                    print(f"[RAID] Erro ao processar Raid JSON: {e}")
                finally:
                    if os.path.exists(LOCAL_GAMEPLAY_CONFIG):
                        os.remove(LOCAL_GAMEPLAY_CONFIG)


def get_base_at(x, z):
    """Verifica se existe uma base nas coordenadas e retorna o dono."""
    bases = database.get_security_bases()
    for base in bases:
        dist = math.sqrt((x - base["x"]) ** 2 + (z - base["z"]) ** 2)
        if dist <= base["radius"]:
            return base
    return None


async def parse_log_line(line):
    """Processa uma linha do log e aplica as regras de segurança."""
    line = line.strip()
    if not line:
        return

    from auto_ban_system import ban_player_immediate

    # 0. DETECÇÃO DE LOGIN (Captura de XUID)
    # Ex: 10:20:30 | Player "Nome" (id=HASH pos=<...>) connected
    if "connected" in line.lower() and "player" in line.lower():
        pattern_login = r'Player "(?P<name>[^"]+)" \(id=(?P<xuid>[^ ]+) pos='
        match_login = re.search(pattern_login, line)
        if match_login:
            p_name = match_login.group("name")
            p_xuid = match_login.group("xuid")
            database.update_player_identity(p_name, p_xuid)
            print(f"[SYNC] Identidade sincronizada: {p_name} ({p_xuid})")
            return

    # Regex para extrair Jogador, Coordenadas e o Resto da linha
    pattern = r'Player "(?P<name>[^"]+)" \(id=[^ ]+ pos=<(?P<coords>[^>]+)>\)(?P<action_line>.+)'
    match = re.search(pattern, line)

    if not match:
        # Tentar formato alternativo (alguns logs tem espaço antes do Built ou usam 'at <')
        pattern_alt = r'Player "(?P<name>[^"]+)" .*(?:at|pos)=<(?P<coords>[^>]+)>.*'
        match = re.search(pattern_alt, line)
        if not match:
            return

    player_name = match.group("name")
    coords_str = match.group("coords")
    action_line = (
        match.group("action_line") if "action_line" in match.groupdict() else line
    )

    try:
        x, y, z = map(float, coords_str.split(","))
    except:
        return

    action_line_lower = action_line.lower()

    # 1. DETECÇÃO DE CONSTRUÇÃO (built)
    if "built" in action_line_lower:
        base = get_base_at(x, z)
        if not base:
            # Registro Automático na primeira parede construída
            if any(k in action_line_lower for k in ["fence", "gate", "watchtower"]):
                database.register_new_base(player_name, x, z)
                msg = f"🏰 **SOBERANIA REGISTRADA**\nO jogador **{player_name}** construiu sua primeira estrutura e assumiu a soberania em **[{int(x)}, {int(z)}]**.\nÁrea protegida em 50m!"
                await notify_ban(msg)
                print(f"[BASE REGISTERED] {player_name} em {x}, {z}")
        else:
            # Regra de Construção em base alheia
            if base["owner"] != player_name:
                dono_discord = base.get("owner_discord_id")
                if dono_discord:
                    clan_id = database.get_clan_id_by_member(dono_discord)
                    if clan_id:
                        members = database.get_clan_members_gamertags(clan_id)
                        if player_name in members:
                            return

                # INVASÃO!
                msg = f"🚫 **BANIMENTO POR INVASÃO**\nO jogador **{player_name}** tentou construir na base de **{base['owner']}**!"
                await notify_ban(msg)
                ban_player_immediate(
                    player_name,
                    None,
                    f"Invasão de Base: Construindo em área de {base['owner']}",
                    "territory_invasion",
                )

    # 2. DETECÇÃO DE COLOCAÇÃO DE ITENS (placed)
    elif "placed" in action_line_lower:
        parts = re.split(r"placed\s+", action_line, flags=re.IGNORECASE)
        item_name = parts[1].split("<")[0].strip() if len(parts) > 1 else "item"

        base = get_base_at(x, z)
        if base:
            # Colocar item em base alheia
            if base["owner"] != player_name:
                dono_discord = base.get("owner_discord_id")
                if dono_discord:
                    clan_id = database.get_clan_id_by_member(dono_discord)
                    if clan_id:
                        members = database.get_clan_members_gamertags(clan_id)
                        if player_name in members:
                            return

                msg = f"🚫 **BANIMENTO POR INVASÃO**\nO jogador **{player_name}** tentou colocar um item (**{item_name}**) na base de **{base['owner']}**!"
                await notify_ban(msg)
                ban_player_immediate(
                    player_name,
                    None,
                    f"Invasão de Base: Colocando {item_name} na área de {base['owner']}",
                    "territory_invasion",
                )
        elif _is_garden_or_fireplace(item_name):
            # Limite global fora de base
            database.increment_item_count(player_name, item_name)
            count = database.get_item_count(player_name, item_name)
            if count > 2:
                item_type = "plantação" if _is_garden(item_name) else "fogueira"
                msg = f"🚫 **BANIMENTO POR LIMITE**\nO jogador **{player_name}** excedeu o limite global de fogueiras/plantações! Item: **{item_name}**"
                await notify_ban(msg)
                ban_player_immediate(
                    player_name,
                    None,
                    f"Excesso de {item_name} fora de base",
                    "garden_exploit",
                )

    # 3. DETECÇÃO DE RADAR / DISMANTLE
    elif "dismantled" in action_line_lower:
        parts = re.split(r"dismantled\s+", action_line, flags=re.IGNORECASE)
        item_name = parts[1].split(" (")[0].strip() if len(parts) > 1 else "item"

        base = get_base_at(x, z)
        if base and base["owner"] != player_name:
            # Verificar permissões (Clã/Hóspedes)
            dono_discord = base.get("owner_discord_id")
            if dono_discord:
                clan_id = database.get_clan_id_by_member(dono_discord)
                if clan_id:
                    members = database.get_clan_members_gamertags(clan_id)
                    if player_name in members:
                        return

            guests = database.get_base_permissions(base["id"])
            if player_name in guests:
                return

            # Horário de Raid (Sábado 20:00-22:00 BRT)
            br_now = datetime.now(timezone.utc) - timedelta(hours=3)
            is_raid_hours = br_now.weekday() == 5 and 20 <= br_now.hour < 22

            if is_raid_hours:
                # MODO RADAR (Apenas alerta durante o Raid)
                database.add_raid_incident(base["id"], player_name)
                recent_count = database.count_recent_incidents(base["id"])
                if recent_count >= 2:
                    msg = f"📡 **RADAR DE BASE**: Raid em andamento na base de **{base['owner']}**!\n👤 Invasor: `{player_name}`\n📍 local: `{int(x)}, {int(z)}`"
                    await send_radar_alert(msg, base["owner_discord_id"])
            else:
                # FORA DO RAID: Ban Automático
                msg = f"⚔️ **BANIMENTO POR RAID**\nO jogador **{player_name}** foi banido por desmontar estruturas na base de **{base['owner']}** fora do horário!"
                await notify_ban(msg)
                ban_player_immediate(
                    player_name,
                    None,
                    f"Raid em Base Protegida: Desmontando {item_name}",
                    "raid_exploit",
                )

    # 4. DETECÇÃO DE USO DE CAMINHÃO (entered vehicle)
    elif "entered vehicle" in action_line_lower and "truck" in action_line_lower:
        # Check if the coordinates match a known spawn point
        is_spawn_truck = False
        match_x, match_z = int(x), int(z)

        for sx, sz in TRUCK_SPAWNS:
            # Tolerância de 15 metros para o spawn (as vezes o caminhão desliza ou spawna perto)
            if abs(match_x - sx) <= 15 and abs(match_z - sz) <= 15:
                is_spawn_truck = True
                break

        if is_spawn_truck:
            coords_tuple = (match_x, match_z)
            if coords_tuple not in active_truck_timers:
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                active_truck_timers[coords_tuple] = {
                    "expiry": expiry,
                    "player": player_name,
                    "warning_sent": False,
                }

                msg = (
                    f"🚚 **ALERTA DE CAMINHÃO** 🚚\n"
                    f"O jogador **{player_name}** pegou um Caminhão de Kit!\n"
                    f"📍 Local: `[{match_x}, {match_z}]`\n"
                    f"⏳ Tempo de vida: **60 minutos**\n"
                    f"*O caminhão desaparecerá automaticamente em 1 hora.*"
                )
                await notify_truck_alert(msg)
                print(f"[TRUCK] Timer iniciado para {player_name} em {coords_tuple}")


@tasks.loop(minutes=5)
async def monitor_truck_spawns():
    """Verifica se existem caminhoes parados nos spawns (lido do truck_availability.json)."""
    global last_available_trucks
    print("[SCANNER] Verificando novos caminhoes disponiveis...")

    filepath = "truck_availability.json"
    temp_local = "truck_availability_temp.json"

    try:
        # Tenta baixar o arquivo de disponibilidade do servidor
        if download_file(filepath, temp_local):
            with open(temp_local, "r") as f:
                data = json.load(f)

            if "items" in data:
                current_trucks = set()
                for item in data["items"]:
                    # Converter string "X 0 Z" para tupla (X, Z)
                    parts = item["coords"].split()
                    if len(parts) >= 3:
                        tx, tz = int(float(parts[0])), int(float(parts[2]))
                        current_trucks.add((tx, tz))

                # Identificar novos caminhões que não estavam no último scan
                new_trucks = current_trucks - last_available_trucks

                for truck in new_trucks:
                    msg = (
                        f"🚚 **CAMINHÃO DISPONÍVEL!** 🚚\n"
                        f"Um novo Caminhão de Kit foi detectado nos spawns!\n"
                        f"📍 Local: `[{truck[0]}, {truck[1]}]`\n"
                        f"*Corra para garantir o seu!*"
                    )
                    await notify_truck_alert(msg)

                last_available_trucks = current_trucks

            if os.path.exists(temp_local):
                os.remove(temp_local)
    except Exception as e:
        print(f"[SCANNER ERROR] {e}")


async def notify_truck_alert(message):
    """Envia alertas de caminhão para o canal específico."""
    print(f"[TRUCK ALERT] {message}")
    if TRUCK_ALERTS_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(TRUCK_ALERTS_CHANNEL_ID))
            if not channel:
                channel = await bot.fetch_channel(int(TRUCK_ALERTS_CHANNEL_ID))
            if channel:
                await channel.send(message)
        except Exception as e:
            print(f"[TRUCK MSG ERROR] {e}")


@tasks.loop(seconds=30)
async def check_truck_timers():
    """Verifica cronômetros de caminhões e envia comando de delete."""
    now = datetime.now(timezone.utc)
    to_delete = []

    for coords, data in active_truck_timers.items():
        remaining = (data["expiry"] - now).total_seconds()

        # Alerta de 10 minutos
        if 540 <= remaining <= 600 and not data["warning_sent"]:
            msg = f"⚠️ **AVISO**: O caminhão pego por **{data['player']}** em `{coords}` desaparecerá em **10 minutos**!"
            await notify_truck_alert(msg)
            data["warning_sent"] = True

        # Expiração
        if remaining <= 0:
            to_delete.append(coords)

    if to_delete:
        deletion_items = [{"coords": f"{c[0]} 0 {c[1]}"} for c in to_delete]
        payload = {"items": deletion_items}

        # Criar e enviar deletions.json via FTP
        try:
            with open("deletions_temp.json", "w") as f:
                json.dump(payload, f)

            # Subir para o servidor via FTP (na pasta profile do Nitrado)
            if upload_file("deletions_temp.json", "deletions.json"):
                for c in to_delete:
                    msg = f"♻️ **REMOÇÃO**: O caminhão de `{c}` expirou e foi removido para respawn!"
                    await notify_truck_alert(msg)
                    del active_truck_timers[c]
                print(
                    f"[TRUCK] Comando de deleção enviado para {len(to_delete)} caminhões."
                )

            if os.path.exists("deletions_temp.json"):
                os.remove("deletions_temp.json")
        except Exception as e:
            print(f"[TRUCK DELETE ERROR] {e}")


async def notify_admin_log(message):
    """Envia logs de auditoria para o canal administrativo."""
    print(f"[ADMIN LOG] {message}")
    if BAN_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(BAN_CHANNEL_ID))
            if channel:
                await channel.send(message)
        except Exception:
            pass

    # Também envia para o webhook se configurado
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(webhook_url, json={"content": message}, timeout=5)
        except Exception:
            pass


async def notify_ban(message):
    """Envia notificação via Webhook (mais estável) e tenta via Bot Channel."""
    print(f"[NOTIFY] {message}")

    # 1. Tentar via Webhook (Prioridade por ser mais estável)
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(webhook_url, json={"content": message}, timeout=5)
        except Exception as e:
            print(f"[WEBHOOK ERROR] {e}")

    # 2. Tentar via Bot (Redundância)
    if BAN_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(BAN_CHANNEL_ID))
            if not channel:
                channel = await bot.fetch_channel(int(BAN_CHANNEL_ID))
            if channel:
                await channel.send(message)
        except Exception as e:
            print(f"[BOT MSG ERROR] {e}")


async def send_radar_alert(message, owner_discord_id):
    """Envia alertas de radar para o Webhook e DM do dono."""
    print(f"[RADAR] {message}")

    # 1. Enviar para Webhook de Radar (Público/Rastreável)
    if RADAR_WEBHOOK_URL:
        payload = {"content": message}
        # Adicionar menção sonora se tivermos o ID do dono
        if owner_discord_id:
            payload["content"] = f"⚠️ <@{owner_discord_id}> ⚠️\n" + message

        try:
            requests.post(RADAR_WEBHOOK_URL, json=payload, timeout=5)
        except Exception:
            pass

    # 2. Tentar enviar DM para o dono da base
    if owner_discord_id:
        try:
            user = await bot.fetch_user(int(owner_discord_id))
            if user:
                await user.send(
                    f"⚠️ **ALERTA DE BASE** ⚠️\n{message}\n\nEntre no servidor para defender seu patrimônio!"
                )
        except Exception as e:
            print(f"[RADAR ERROR] Nao consegui enviar DM para {owner_discord_id}: {e}")


def find_latest_adm_log(ftp):
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            print(f"[DEBUG] Tentando path: {path}")
            ftp.cwd(path)
            items = ftp.nlst()
            adm_files = [f"{path}/{f}" for f in items if f.lower().endswith(".adm")]
            if adm_files:
                adm_files.sort()
                latest = adm_files[-1]
                print(f"[DEBUG] Encontrado: {latest}")
                return latest
        except Exception as e:
            print(f"[DEBUG] Erro em {path}: {e}")
            continue
    return None


class DissolveClanModal(ui.Modal, title="⚠️ CANCELAR REGISTROS (DELETAR CLÃ)"):
    confirm = ui.TextInput(
        label="Digite 'DELETAR' para confirmar",
        placeholder="DELETAR",
        min_length=7,
        max_length=7,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "DELETAR":
            return await interaction.response.send_message(
                "❌ Confirmação incorreta. O clã não foi deletado.", ephemeral=True
            )

        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "❌ Você não é líder de nenhum clã.", ephemeral=True
            )

        if database.delete_clan_by_leader(interaction.user.id):
            await interaction.response.send_message(
                f"🗑️ **Registros Cancelados!** O clã **{clan_info['name']}** e todos os seus membros foram removidos do sistema. Você já pode criar um novo clã.",
                ephemeral=True,
            )
            await notify_admin_log(
                f"🗑️ **Clã Deletado**: {interaction.user.display_name} dissolveu o clã **{clan_info['name']}**."
            )
        else:
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao tentar deletar o clã.", ephemeral=True
            )


class AddMemberModal(ui.Modal, title="➕ Adicionar Membro ao Clã"):
    gamertag = ui.TextInput(
        label="Gamertag do Amigo",
        placeholder="Ex: PlayerFriend123",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "❌ Apenas o líder pode adicionar membros.", ephemeral=True
            )

        # Adiciona ao clã (ID 0 no Discord pois é registro manual/via gamertag)
        database.add_clan_member(clan_info["id"], "0", self.gamertag.value)

        await interaction.response.send_message(
            f"✅ **Sucesso!** O jogador `{self.gamertag.value}` agora faz parte do clã **{clan_info['name']}** e está autorizado em suas bases.",
            ephemeral=True,
        )
        await notify_admin_log(
            f"👥 **Membro Manual**: {interaction.user.display_name} adicionou `{self.gamertag.value}` ao clã **{clan_info['name']}**."
        )


class CreateClanModal(ui.Modal, title="🚩 Registrar Novo Clã"):
    clan_name = ui.TextInput(
        label="Nome do Clã",
        placeholder="Ex: Os Vingadores",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        leader_discord_id = interaction.user.id
        leader_gamertag = database.get_gamertag_by_discord(leader_discord_id)

        if not leader_gamertag:
            return await interaction.response.send_message(
                "❌ Você precisa vincular sua Gamertag primeiro!", ephemeral=True
            )

        existing_clan = database.get_clan_by_leader(leader_discord_id)
        if existing_clan:
            return await interaction.response.send_message(
                f"❌ Você já é líder do clã **{existing_clan['name']}**!",
                ephemeral=True,
            )

        clan_id = database.create_clan(self.clan_name.value, leader_discord_id)
        database.add_clan_member(clan_id, leader_discord_id, leader_gamertag)

        await interaction.response.send_message(
            f"✅ **Sucesso!** O clã **{self.clan_name.value}** foi registrado e você é o líder!",
            ephemeral=True,
        )
        await notify_admin_log(
            f"🚩 **Novo Clã**: {interaction.user.display_name} criou o clã **{self.clan_name.value}**."
        )


class LinkGamertagModal(ui.Modal, title="🔗 Vincular Gamertag Xbox"):
    gamertag = ui.TextInput(
        label="Sua Gamertag Xbox",
        placeholder="Ex: Player123",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        discord_id = interaction.user.id
        gamertag_value = self.gamertag.value

        # Verifica se a gamertag já está vinculada a outro Discord ID
        existing_discord_id = database.get_discord_id_by_gamertag(gamertag_value)
        if existing_discord_id and existing_discord_id != discord_id:
            return await interaction.response.send_message(
                f"❌ A Gamertag `{gamertag_value}` já está vinculada a outro usuário do Discord.",
                ephemeral=True,
            )

        # Verifica se o Discord ID já tem uma gamertag vinculada
        existing_gamertag = database.get_gamertag_by_discord(discord_id)
        if existing_gamertag and existing_gamertag != gamertag_value:
            # Se já tem, atualiza
            database.update_gamertag_link(discord_id, gamertag_value)
            await interaction.response.send_message(
                f"✅ Sua Gamertag foi atualizada para `{gamertag_value}`!",
                ephemeral=True,
            )
            await notify_admin_log(
                f"🔗 **Gamertag Atualizada**: {interaction.user.display_name} atualizou para `{gamertag_value}`."
            )
            return

        # Se não tem, cria o vínculo
        database.link_gamertag(discord_id, gamertag_value)

        # Adiciona o cargo de verificado
        if VERIFIED_ROLE_ID:
            try:
                role = interaction.guild.get_role(int(VERIFIED_ROLE_ID))
                if role:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(
                        f"✅ Sua Gamertag `{gamertag_value}` foi vinculada com sucesso e você recebeu o cargo de Verificado!",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"✅ Sua Gamertag `{gamertag_value}` foi vinculada com sucesso! (Cargo de verificado não encontrado)",
                        ephemeral=True,
                    )
            except Exception as e:
                print(f"Erro ao adicionar cargo de verificado: {e}")
                await interaction.response.send_message(
                    f"✅ Sua Gamertag `{gamertag_value}` foi vinculada com sucesso! (Erro ao adicionar cargo)",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                f"✅ Sua Gamertag `{gamertag_value}` foi vinculada com sucesso!",
                ephemeral=True,
            )
        await notify_admin_log(
            f"🔗 **Nova Gamertag**: {interaction.user.display_name} vinculou `{gamertag_value}`."
        )


@tasks.loop(seconds=15)
async def monitor_logs():
    global last_byte_offset, current_log_file
    print("[DEBUG] Loop de logs iniciado...")
    ftp = connect_ftp()
    if not ftp:
        print("[DEBUG] Falha ao conectar no FTP.")
        return

    try:
        # SEMPRE procura o arquivo mais recente para detectar novos logs (Nitrado muda nome no restart)
        latest_candidate = find_latest_adm_log(ftp)

        if not latest_candidate:
            print("[DEBUG] Nenhum arquivo ADM encontrado.")
            return

        # Se o arquivo mudou, resetamos o offset
        if latest_candidate != current_log_file:
            print(f"[DEBUG] Novo log detectado ou mudanca: {latest_candidate}")
            current_log_file = latest_candidate
            ftp.voidcmd("TYPE I")
            last_byte_offset = ftp.size(current_log_file)
            print(
                f"[DEBUG] Monitorando agora: {current_log_file} (Offset: {last_byte_offset})"
            )
            return  # Esperamos a proxima iteração para ler

        if current_log_file:
            ftp.voidcmd("TYPE I")
            server_size = ftp.size(current_log_file)
            print(
                f"[DEBUG] Check: {current_log_file} | Server: {server_size} | Local: {last_byte_offset}"
            )

            # Detecção de Wipe/Reset (tamanho diminuiu no mesmo arquivo)
            if server_size < last_byte_offset:
                print("[DEBUG] Log resetado (tamanho menor no mesmo arquivo)!")
                last_byte_offset = 0

            # Se houver conteúdo novo
            if server_size > last_byte_offset:
                diff = server_size - last_byte_offset
                print(f"[MONITOR] Lendo {diff} novos bytes de {current_log_file}")

                bio = io.BytesIO()
                ftp.retrbinary(
                    f"RETR {current_log_file}", bio.write, rest=last_byte_offset
                )
                new_content = bio.getvalue().decode("utf-8", errors="ignore")
                for line in new_content.split("\n"):
                    if line.strip():
                        await parse_log_line(line)
                last_byte_offset = server_size
    except Exception as e:
        print(f"Log Error: {e}")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


@bot.event
async def on_ready():
    print(f"[EVENT] Bot ready: {bot.user}")
    bot.add_view(ClanPortalView())  # Mantém os botões funcionando após reiniciar

    # Configuração de Canal e Envio do Portal Automático
    if PORTAL_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(PORTAL_CHANNEL_ID))
            if channel:
                # Limpa mensagens antigas do próprio bot para manter o canal limpo
                async for message in channel.history(limit=5):
                    if message.author == bot.user:
                        await message.delete()

                # Recria o Portal
                embed = discord.Embed(
                    title="🏆 Portal de Clãs - Brasil Sul",
                    description=(
                        "Centralize sua gestão aqui!\n\n"
                        "**1.** Use o botão azul para vincular seu Xbox.\n"
                        "**2.** Use o botão verde para registrar seu clã.\n"
                        "**3.** Use o botão azul (Adicionar) para cadastrar os Gamertags de seus amigos no seu clã.\n"
                        "**4.** Use o botão cinza para aceitar convites pendentes.\n"
                        "**5.** Use o botão vermelho para **CANCELAR REGISTROS** e apagar seu clã atual.\n\n"
                        "*Ação de líder: Ao adicionar um membro, ele é liberado automaticamente no Radar da sua base.*"
                    ),
                    color=discord.Color.gold(),
                )
                await channel.send(embed=embed, view=ClanPortalView())
                print(
                    f"[PORTAL] Enviado automaticamente para o canal {PORTAL_CHANNEL_ID}"
                )

                # Convite Automático
                invite = await channel.create_invite(
                    max_age=0, max_uses=0, unique=False, reason="Auto Setup"
                )
                print(f"[INVITE] Convite ativo: {invite.url}")
                await notify_admin_log(
                    f"🚀 **Bot VPS Reiniciado**: Portal atualizado no canal."
                )
            else:
                print(f"[ERROR] Canal {PORTAL_CHANNEL_ID} não encontrado.")
        except Exception as e:
            print(f"[ERROR Portal Setup] {e}")

    # Configuração de Canal e Envio das Regras Automático
    if RULES_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(RULES_CHANNEL_ID))
            if channel:
                # Limpa mensagens antigas do próprio bot
                async for message in channel.history(limit=5):
                    if message.author == bot.user:
                        await message.delete()

                # Envia as Regras
                embed = discord.Embed(
                    title="📜 REGRAS OFICIAIS - BRASIL SUL",
                    description=(
                        "**1. Raid Tático Liberado** ⚔️\n"
                        "O Raid é permitido apenas aos **Sábados das 20:00 às 22:00 (BRT)**. "
                        "Rams e invasões técnicas são permitidas pois o servidor possui **Radar Ativo**.\n\n"
                        "**2. Construção Militar** 🏗️\n"
                        "É permitido construir em áreas militares, inclusive no bunker e áreas do litoral.\n\n"
                        "**3. Registro de Bases Automatizado** 🛡️\n"
                        "A partir do momento que você **constrói sua primeira parede**, o sistema registra a soberania. "
                        "Apenas o seu perfil (e seu clã cadastrado) poderá construir ou mover itens (barracas, baús, tendas, fogueiras, etc) na área. "
                        "Invasores tentando construir ou fazer glitch serão **punidos automaticamente**.\n\n"
                        "**4. Cadastro de Clã (IMPORTANTE)** 🔗\n"
                        "Use o canal **🔗 LINK PERMANENTE** para registrar seu perfil, seu clã e gerenciar seus membros. "
                        "Isso garante que seus amigos não sejam banidos por engano na sua base.\n\n"
                        "**5. Kits e Clima** 🚚☀️\n"
                        "• Caminhão Kit Base espalhado em locais de spawn.\n"
                        "• Sem chuva, noites curtas e dias longos.\n\n"
                        "*Sem mimimi e sem choro. O sistema é justo e automático!*"
                    ),
                    color=discord.Color.orange(),
                )
                embed.set_footer(text="Servidor 24/7 Security System")
                await channel.send(embed=embed)
                print(
                    f"[RULES] Enviadas automaticamente para o canal {RULES_CHANNEL_ID}"
                )
            else:
                print(f"[ERROR] Canal de regras {RULES_CHANNEL_ID} não encontrado.")
        except Exception as e:
            print(f"[ERROR Rules Setup] {e}")

    # Inicialização de Sistemas
    print("[INIT] Aplicando free building...")
    await enforce_free_building()

    if not monitor_logs.is_running():
        monitor_logs.start()
        print("[INIT] Monitor de logs iniciado.")
    if not raid_scheduler.is_running():
        raid_scheduler.start()
        print("[INIT] Agendador de raid iniciado.")
    if not check_truck_timers.is_running():
        check_truck_timers.start()
        print("[INIT] Monitor de timers de caminhao iniciado.")
    if not monitor_truck_spawns.is_running():
        monitor_truck_spawns.start()
        print("[INIT] Scanner de novos caminhoes iniciado.")

    print("[INIT] 🚀 Bot VPS totalmente operacional!")


async def main():
    async with bot:
        database.init_db()
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[EXIT] Bot encerrado manualmente.")
