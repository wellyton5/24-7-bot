import fcntl, sys, os, io, json, math, re, requests, asyncio
from dotenv import load_dotenv
import discord
from discord import ui
from discord.ext import tasks, commands
from datetime import datetime, timedelta, timezone

# Importar auxiliares locais
import database
from ftp_helpers import connect_ftp, download_file, upload_file
from chernarus_locations import get_nearest_location
import glitch_detector

load_dotenv()

# Singleton Lock
fp = open("/tmp/bot_24_7.lock", "w")
try:
    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    sys.exit(0)

TOKEN = os.getenv("DISCORD_TOKEN")
BAN_CHANNEL_ID = os.getenv("BAN_CHANNEL")
RADAR_WEBHOOK_URL = os.getenv("RADAR_WEBHOOK_URL")
TRUCK_ALERTS_CHANNEL_ID = os.getenv("TRUCK_ALERTS_CHANNEL_ID")
GAMEPLAY_CONFIG_PATH = "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json"
LOCAL_GAMEPLAY_CONFIG = "cfggameplay_temp.json"

# Variáveis globais
last_byte_offset = 0
current_log_file = None
active_truck_timers = {}  # {coords: timestamp_to_delete}
pending_deletions = []  # [(coords, timestamp_ready)]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- MODALS ---


class LinkGamertagModal(ui.Modal, title="🔗 Vincular Gamertag Xbox"):
    gamertag = ui.TextInput(
        label="Sua Gamertag Xbox",
        placeholder="Ex: Player123",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        database.link_gamertag(interaction.user.id, self.gamertag.value)

        # Auto-vínculo de clã pendente
        pending = database.get_pending_clan_by_gamertag(self.gamertag.value)
        clan_msg = ""
        if pending:
            clan_id = pending[0]
            database.add_clan_member(clan_id, interaction.user.id, self.gamertag.value)
            clan_msg = "\n🎊 Notei que você já foi pré-adicionado a um clã! Vínculo concluído automaticamente."

        await interaction.response.send_message(
            f"[V] Gamertag `{self.gamertag.value}` vinculada!{clan_msg}", ephemeral=True
        )


class CreateClanModal(ui.Modal, title="🚩 Registrar Novo Clã"):
    name = ui.TextInput(
        label="Nome do Clã",
        placeholder="Ex: Os Vingadores",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        leader_gt = database.get_gamertag_by_discord(interaction.user.id)
        if not leader_gt:
            return await interaction.response.send_message(
                "[X] Vincule seu Xbox primeiro.", ephemeral=True
            )
        cid = database.create_clan(self.name.value, interaction.user.id)
        if cid:
            database.add_clan_member(cid, interaction.user.id, leader_gt)
            await interaction.response.send_message(
                f"[V] Clã **{self.name.value}** criado!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "[X] Esse nome de clã já existe.", ephemeral=True
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
                "[X] Erro de permissão.", ephemeral=True
            )
        database.add_clan_member(clan_info["id"], None, self.gamertag.value)
        await interaction.response.send_message(
            f"[V] Jogador `{self.gamertag.value}` pré-adicionado ao clã! Ele só precisa vincular a Gamertag no Discord agora.",
            ephemeral=True,
        )


class DissolveClanModal(ui.Modal, title="[!] DELETAR CLÃ"):
    confirm = ui.TextInput(
        label="Digite 'DELETAR' para confirmar",
        placeholder="DELETAR",
        min_length=7,
        max_length=7,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "DELETAR":
            return await interaction.response.send_message(
                "[X] Confirmação incorreta.", ephemeral=True
            )
        if database.delete_clan_by_leader(interaction.user.id):
            await interaction.response.send_message(
                "🗑️ Registros cancelados com sucesso.", ephemeral=True
            )


# --- VIEW ---


class ClanPortalView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="🔗 Vincular Gamertag",
        style=discord.ButtonStyle.blurple,
        custom_id="portal:link_gamertag",
    )
    async def link_gamertag_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.send_modal(LinkGamertagModal())

    @ui.button(
        label="🚩 Registrar Meu Clã",
        style=discord.ButtonStyle.success,
        custom_id="portal:create_clan",
    )
    async def create_clan_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.send_modal(CreateClanModal())

    @ui.button(
        label="➕ Adicionar Membro",
        style=discord.ButtonStyle.primary,
        custom_id="portal:add_member",
    )
    async def add_member_btn(self, interaction: discord.Interaction, button: ui.Button):
        clan_info = database.get_clan_by_leader(interaction.user.id)
        if not clan_info:
            return await interaction.response.send_message(
                "[X] Você precisa ser líder de um clã!", ephemeral=True
            )
        await interaction.response.send_modal(AddMemberModal())

    @ui.button(
        label="📩 Aceitar Convite",
        style=discord.ButtonStyle.secondary,
        custom_id="portal:accept_invite",
    )
    async def accept_invite_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        invites = database.get_pending_invites(interaction.user.id)
        if not invites:
            return await interaction.response.send_message(
                "[X] Nenhum convite pendente.", ephemeral=True
            )
        invite = invites[0]
        gt = database.get_gamertag_by_discord(interaction.user.id)
        if not gt:
            return await interaction.response.send_message(
                "[X] Vincule seu Xbox primeiro!", ephemeral=True
            )
        database.add_clan_member(invite["clan_id"], interaction.user.id, gt)
        database.delete_invite(invite["id"])
        await interaction.response.send_message(
            f"🎉 Bem-vindo ao clã **{invite['clan_name']}**!", ephemeral=True
        )

    @ui.button(
        label="🗑️ CANCELAR REGISTROS",
        style=discord.ButtonStyle.danger,
        custom_id="portal:dissolve_clan",
    )
    async def dissolve_clan_btn(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.send_modal(DissolveClanModal())


# --- SECURITY LOGIC ---


async def parse_log_line(line):
    """Processa uma linha do log e aplica as regras de segurança."""
    line = line.strip()
    if not line:
        return

    # 0. DETECÇÃO DE LOGIN (Captura de XUID e Identidade - AltDetector Style)
    # Ex: 10:20:30 | Player "Nome"(id=HASH pos=<...>) connected
    # Ex: 10:20:30 | Player "Nome"(id=HASH pos=<...>) is connected from IP:PORT
    if "connected" in line.lower() and "player" in line.lower():
        pattern_login = r'Player "(?P<name>[^"]+)"\(id=(?P<xuid>[^ ]+).+connected( from (?P<ip>[\d\.]+):)?'
        match_login = re.search(pattern_login, line)
        if match_login:
            p_name = match_login.group("name")
            p_xuid = match_login.group("xuid")
            p_ip = match_login.group("ip")
            database.log_connection(p_name, p_ip, p_xuid)
            print(
                f"[SYNC] Identidade sincronizada: {p_name} ({p_xuid}) | IP: {p_ip or 'N/A'}"
            )
            return

    # Regex para extrair Jogador, Coordenadas e o Resto da linha
    pattern = r'Player "(?P<name>[^"]+)" \(id=[^ ]+ pos=<(?P<coords>[^>]+)>\)(?P<action_line>.+)'
    match = re.search(pattern, line)

    if not match:
        return

    player_name = match.group("name")
    coords_str = match.group("coords")
    action_line = match.group("action_line")

    try:
        x, y, z = map(float, coords_str.split(","))
    except:
        return

    action_line_lower = action_line.lower()

    # 1. DETECÇÃO DE CONSTRUÇÃO (Soberania Automática)
    if "built" in action_line_lower:
        base = database.get_base_at(x, z)
        if not base:
            if any(k in action_line_lower for k in ["fence", "gate", "watchtower"]):
                database.register_new_base(player_name, x, z)
                print(f"[BASE REGISTERED] {player_name} em {x}, {z}")
        else:
            if base["owner"] != player_name:
                # Verificar se está no clã
                clan_id = database.get_clan_id_by_member(
                    database.get_discord_by_gamertag(player_name)
                )  # Placeholder
                # Log de invasão aqui se necessário

        # 2. DETECÇÃO DE COLOCAÇÃO DE ITENS (placed)
        elif "placed" in action_line_lower:
            parts = re.split(r"placed\s+", action_line, flags=re.IGNORECASE)
            item_raw = parts[1].strip() if len(parts) > 1 else ""

            # Extrair nome amigável ou classe técnica
            if "<" in item_raw:
                friendly_name = item_raw.split("<")[0].strip()
                class_name = item_raw.split("<")[1].split(">")[0].strip()
                # Se for "Nameless Object", usamos a classe técnica
                item_name = class_name if friendly_name.lower() == "nameless object" else friendly_name
            else:
                item_name = item_raw if item_raw else "item"

            base = database.get_base_at(x, z)
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
                    from auto_ban_system import ban_player_immediate

                    ban_player_immediate(
                        player_name,
                        _player_id_cache.get(player_name),
                        f"Invasão de Base: Colocando {item_name} na área de {base['owner']}",
                        "territory_invasion",
                    )
            elif _is_garden_or_fireplace(item_name):
                # Limite global fora de base (ZERO TOLERANCE)
                database.increment_item_count(player_name, item_name)
                count = database.get_item_count(player_name, item_name)
                if count >= 1:
                    msg = f"🚫 **BANIMENTO POR LIMITE (ZERO TOLERANCE)**\nO jogador **{player_name}** tentou colocar um item proibido fora de base! Item: **{item_name}**"
                    await notify_ban(msg)
                    from auto_ban_system import ban_player_immediate

                    ban_player_immediate(
                        player_name,
                        _player_id_cache.get(player_name),
                        f"Uso de {item_name} fora de base (Proibido)",
                        "garden_exploit",
                    )

        # 3. DETECÇÃO DE INTERAÇÃO COM VEÍCULO (Auto-Delete Plan)
        # Ex: 21:41:58 | Player "Nome" (...) Mounted BarbedWire on Fence (Não é isso)
        # O ADM log do DayZ Xbox mostra entrada em veículo assim:
        # "into" costuma ser log de tiro. Para veículos vamos procurar "mounted" associado a tipos de caminhão
        if "mounted" in action_line_lower and any(
            v in action_line for v in ["Truck", "M3S", "V3S", "CivilianSedan", "Hatchback"]
        ):
            # Um jogador interagiu com um caminhão
            # Agendar deleção para 60 minutos
            delete_time = datetime.now() + timedelta(hours=1)
            active_truck_timers[coords_str] = delete_time
            print(f"[TRUCK] Deleção agendada para {coords_str} às {delete_time}")

            # Notificar no canal de segurança (Radar)
            webhook_content = {
                "embeds": [
                    {
                        "title": "🚚 Caminhão em Uso",
                        "description": f"O jogador **{player_name}** entrou em um caminhão em `{coords_str}`.\nEle será deletado automaticamente em 1 hora para respawnar.",
                        "color": 16753920,  # Orange
                    }
                ]
            }
            try:
                requests.post(RADAR_WEBHOOK_URL, json=webhook_content)
            except:
                pass


# --- MONITORING ---


def find_latest_adm_log(ftp):
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            adms = sorted([f"{path}/{f}" for f in items if f.endswith(".adm")])
            if adms:
                return adms[-1]
        except:
            continue
    return None


@tasks.loop(minutes=10)
async def truck_status_task():
    """Monitora a disponibilidade de caminhões via FTP."""
    if not TRUCK_ALERTS_CHANNEL_ID:
        return

    ftp = connect_ftp()
    if not ftp:
        return

    try:
        filepath = None
        # O scanner no init.c salva como $profile:truck_availability.json
        for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
            try:
                ftp.cwd(path)
                items = ftp.nlst()
                if "truck_availability.json" in items:
                    filepath = f"{path}/truck_availability.json"
                    break
            except:
                continue

        if filepath:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {filepath}", bio.write)
            data = json.loads(bio.getvalue().decode("utf-8"))

            items = data.get("items", [])
            count = len(items)

            channel = bot.get_channel(int(TRUCK_ALERTS_CHANNEL_ID))
            if channel:
                embed = discord.Embed(
                    title="🚚 Status dos Caminhões (Kit Base)",
                    description=f"O scanner do servidor encontrou **{count}** caminhões disponíveis nos spawns.",
                    color=discord.Color.blue() if count > 0 else discord.Color.red(),
                    timestamp=datetime.now(),
                )

                if count > 0:
                    coords_list = ""
                    # Mostrar as primeiras 15 coordenadas para não poluir muito
                    for i, item in enumerate(items[:15]):
                        loc_name = get_nearest_location(item["coords"])
                        driver_info = ""
                        if item.get("driver"):
                            driver_info = f" 🚨 [Ocupado: {item['driver']}]"

                        coords_list += f"📍 **{i + 1}**: `{item['coords']}` ({loc_name}){driver_info}\n"

                    embed.add_field(
                        name="Localizações Ativas (Coordenadas)",
                        value=coords_list,
                        inline=False,
                    )
                    if count > 15:
                        embed.set_footer(
                            text=f"E mais {count - 15} caminhões em outros spawns."
                        )
                else:
                    embed.add_field(
                        name="Aviso",
                        value="Nenhum caminhão disponível nos spawns no momento.",
                        inline=False,
                    )

                await channel.send(embed=embed)
                print(
                    f"[TRUCK SCAN] {count} encontrados e reportados no canal {TRUCK_ALERTS_CHANNEL_ID}"
                )
    except Exception as e:
        print(f"[TRUCK ERROR] {e}")
    finally:
        try:
            ftp.quit()
        except:
            pass


@tasks.loop(seconds=60)
async def vehicle_delete_scheduler():
    """Verifica se há caminhões esperando para serem deletados."""
    now = datetime.now()
    to_remove = []

    # Criar uma cópia para evitar erro de mudança de tamanho durante iteração
    timers_copy = list(active_truck_timers.items())

    for coords, delete_at in timers_copy:
        if now >= delete_at:
            pending_deletions.append(coords)
            to_remove.append(coords)

    for coords in to_remove:
        del active_truck_timers[coords]

    if pending_deletions:
        await execute_auto_deletions()


def _is_garden(item_name):
    garden_keywords = [
        "GardenPlot",
        "Greenhouse",
        "Planting",
        "Vegetable",
        "Plot",
        "Farming",
    ]
    return any(kw.lower() in item_name.lower() for kw in garden_keywords)


def _is_fireplace(item_name):
    fireplace_keywords = ["Fireplace", "Oven", "Stove", "Barrel", "Campfire", "Fire"]
    item_lower = item_name.lower()
    if "barrel" in item_lower and "hole" in item_lower:
        return True
    return any(kw.lower() in item_lower for kw in fireplace_keywords)


def _is_garden_or_fireplace(item_name):
    return _is_garden(item_name) or _is_fireplace(item_name)


async def execute_auto_deletions():
    """Gera o arquivo deletions.json e sobe via FTP para o servidor."""
    global pending_deletions
    if not pending_deletions:
        return

    # Limitar a 10 deleções por vez para não pesar
    batch = list(set(pending_deletions[:10]))
    pending_deletions = pending_deletions[10:]

    if not batch:
        return

    data = {"items": [{"coords": c} for c in batch]}
    json_content = json.dumps(data, indent=2)

    # Salvar temporariamente
    temp_file = "deletions_temp.json"
    with open(temp_file, "w") as f:
        f.write(json_content)

    # Enviar via FTP
    ftp = connect_ftp()
    if ftp:
        try:
            # Enviar para a pasta que o init.c mapeia como $profile
            for path in ["/dayzxb/config", "/dayzxb"]:
                try:
                    ftp.cwd(path)
                    with open(temp_file, "rb") as f:
                        ftp.storbinary("STOR deletions.json", f)
                    print(f"[AUTO-DELETE] Comando de deleção enviado para {path}")
                    break
                except:
                    continue

            # Notificar no Discord
            webhook_content = {
                "embeds": [
                    {
                        "title": "🗑️ Deleção Concluída",
                        "description": f"O sistema removeu **{len(batch)}** caminhão(ões) para garantir o respawn aleatório.",
                        "color": 3066993,  # Green
                    }
                ]
            }
            try:
                requests.post(RADAR_WEBHOOK_URL, json=webhook_content)
            except:
                pass

        except Exception as e:
            print(f"[FTP ERROR] Falha ao enviar deleções: {e}")
        finally:
            ftp.quit()

    # Limpar arquivo temporário
    if os.path.exists(temp_file):
        os.remove(temp_file)


@tasks.loop(seconds=30)
async def monitor_logs():
    global last_byte_offset, current_log_file
    ftp = connect_ftp()
    if not ftp:
        return
    try:
        latest = find_latest_adm_log(ftp)
        if not latest:
            return
        if latest != current_log_file:
            current_log_file = latest
            last_byte_offset = ftp.size(latest)
            return
        sz = ftp.size(latest)
        if sz > last_byte_offset:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {latest}", bio.write, rest=last_byte_offset)
            last_byte_offset = sz

            lines = bio.getvalue().decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                if line.strip():
                    await parse_log_line(line)
    except:
        pass
    finally:
        try:
            ftp.quit()
        except:
            pass


# --- COMANDS ---


@bot.group(name="clan", invoke_without_command=True)
async def clan(ctx):
    """Grupo de comandos para gestão de clãs."""
    await ctx.send(
        "[DOC] **Comandos de Clã:**\n"
        "`!clan criar <nome>` - Cria um novo clã\n"
        "`!clan convidar @membro` - Envia um convite para um membro\n"
        "`!clan aceitar` - Aceita um convite pendente\n"
        "`!clan lista` - Lista todos os clãs registrados\n"
        "`!clan sair` - Sai do clã atual\n\n"
        "🕵️‍♂️ **Segurança (Admin):**\n"
        "`!lookup <gamertag>` - Ficha completa do jogador\n"
        "`!alts <gamertag>` - Detecta contas secundárias"
    )


@clan.command(name="lista")
async def clan_lista(ctx):
    clans = database.get_all_clans()
    if not clans:
        return await ctx.send("📭 Nenhum clã registrado.")
    msg = "🏆 **Clãs Registrados:**\n"
    for c in clans:
        msg += f"• **{c['name']}** (ID: {c['id']})\n"
    await ctx.send(msg)


@clan.command(name="criar")
async def clan_criar(ctx, *, name: str):
    if database.get_clan_by_leader(ctx.author.id):
        return await ctx.send("[X] Você já é líder de um clã!")
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send("[X] Vincule seu Xbox primeiro!")
    cid = database.create_clan(name, ctx.author.id)
    if cid:
        database.add_clan_member(cid, ctx.author.id, gt)
        await ctx.send(f"[V] Clã **{name}** criado!")
    else:
        await ctx.send("[X] Esse nome já existe.")


@clan.command(name="convidar")
async def clan_convidar(ctx, member: discord.Member):
    clan_info = database.get_clan_by_leader(ctx.author.id)
    if not clan_info:
        return await ctx.send("[X] Apenas líderes podem convidar.")
    if database.create_clan_invite(clan_info["id"], member.id):
        await ctx.send(
            f"📩 {member.mention}, você foi convidado para o clã **{clan_info['name']}**!"
        )
    else:
        await ctx.send("[X] Erro ou convite já enviado.")


@bot.command(name="lookup")
@commands.has_permissions(administrator=True)
async def lookup(ctx, *, gamertag: str):
    """Consulta a ficha completa de um jogador (AltDetector style)."""
    identity = database.get_player_identity(gamertag)
    if not identity:
        return await ctx.send(
            f"[X] Jogador `{gamertag}` não encontrado no banco de dados."
        )

    alts = database.find_alts(gamertag)
    alts_str = ", ".join([f"`{a}`" for a in alts]) if alts else "Nenhum alt detectado."

    embed = discord.Embed(
        title=f"🔍 Detalhes do Jogador: {gamertag}", color=discord.Color.blue()
    )
    embed.add_field(name="🎮 Gamertag", value=identity["gamertag"], inline=True)
    embed.add_field(
        name="🆔 Account ID (XUID)",
        value=f"`{identity['xuid'] or 'Desconhecido'}`",
        inline=False,
    )
    embed.add_field(
        name="🌐 Último IP",
        value=f"`{identity['last_ip'] or 'Não capturado'}`",
        inline=True,
    )
    embed.add_field(
        name="📱 Device ID",
        value=f"`{identity['device_id'] or 'Não capturado'}`",
        inline=False,
    )
    embed.add_field(
        name="🕒 Última Vez Visto", value=identity["last_seen"], inline=True
    )
    embed.add_field(name="👥 Contas Vinculadas (Alts)", value=alts_str, inline=False)

    embed.set_footer(text="BigodeTexas Security System - AltDetector Module")
    await ctx.send(embed=embed)


@bot.command(name="alts")
@commands.has_permissions(administrator=True)
async def alts(ctx, *, gamertag: str):
    """Busca rápida por contas secundárias."""
    alts_list = database.find_alts(gamertag)
    if not alts_list:
        await ctx.send(f"[V] Nenhuma conta secundária encontrada para `{gamertag}`.")
    else:
        msg = f"[!] **Contas vinculadas encontradas para `{gamertag}`:**\n"
        for i, alt in enumerate(alts_list, 1):
            msg += f"{i}. `{alt}`\n"
        await ctx.send(msg)


@bot.command(name="aceitar")
async def clan_aceitar(ctx):
    invites = database.get_pending_invites(ctx.author.id)
    if not invites:
        return await ctx.send("[X] Nenhum convite pendente.")
    invite = invites[0]
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send("[X] Vincule seu Xbox primeiro!")
    database.add_clan_member(invite["clan_id"], ctx.author.id, gt)
    database.delete_invite(invite["id"])
    await ctx.send(f"🎉 Bem-vindo ao clã **{invite['clan_name']}**!")


@bot.command(name="regras")
@commands.has_permissions(administrator=True)
async def portal(ctx):
    embed = discord.Embed(
        title="🏆 Portal de Clãs - Brasil Sul",
        description=(
            "**1.** Vincule seu Xbox (Botão Azul)\n"
            "**2.** Registre seu clã (Botão Verde)\n"
            "**3.** Adicione amigos (Botão Azul Claro)\n"
            "**4.** Aceite convites (Botão Cinza)\n"
            "**5.** Cancele registros (Botão Vermelho)"
        ),
        color=discord.Color.gold(),
    )
    await ctx.send(embed=embed, view=ClanPortalView())


@bot.event
async def on_ready():
    bot.add_view(ClanPortalView())
    if not monitor_logs.is_running():
        monitor_logs.start()
    if not truck_status_task.is_running():
        truck_status_task.start()
    if not vehicle_delete_scheduler.is_running():
        vehicle_delete_scheduler.start()
    print(f"Bot pronto: {bot.user}")


async def main():
    async with bot:
        database.init_db()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
