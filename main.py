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
active_truck_timers = {}

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
        await interaction.response.send_message(
            f"✅ Gamertag `{self.gamertag.value}` vinculada!", ephemeral=True
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
                "❌ Vincule seu Xbox primeiro.", ephemeral=True
            )
        cid = database.create_clan(self.name.value, interaction.user.id)
        if cid:
            database.add_clan_member(cid, interaction.user.id, leader_gt)
            await interaction.response.send_message(
                f"✅ Clã **{self.name.value}** criado!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Esse nome de clã já existe.", ephemeral=True
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
                "❌ Erro de permissão.", ephemeral=True
            )
        database.add_clan_member(clan_info["id"], "0", self.gamertag.value)
        await interaction.response.send_message(
            f"✅ Jogador `{self.gamertag.value}` adicionado!", ephemeral=True
        )


class DissolveClanModal(ui.Modal, title="⚠️ DELETAR CLÃ"):
    confirm = ui.TextInput(
        label="Digite 'DELETAR' para confirmar",
        placeholder="DELETAR",
        min_length=7,
        max_length=7,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "DELETAR":
            return await interaction.response.send_message(
                "❌ Confirmação incorreta.", ephemeral=True
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
                "❌ Você precisa ser líder de um clã!", ephemeral=True
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
                "❌ Nenhum convite pendente.", ephemeral=True
            )
        invite = invites[0]
        gt = database.get_gamertag_by_discord(interaction.user.id)
        if not gt:
            return await interaction.response.send_message(
                "❌ Vincule seu Xbox primeiro!", ephemeral=True
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
        "📜 **Comandos de Clã:**\n"
        "`!clan criar <nome>` - Cria um novo clã\n"
        "`!clan convidar @membro` - Envia um convite para um membro\n"
        "`!clan aceitar` - Aceita um convite pendente\n"
        "`!clan lista` - Lista todos os clãs registrados\n"
        "`!clan sair` - Sai do clã atual"
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
        return await ctx.send("❌ Você já é líder de um clã!")
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send("❌ Vincule seu Xbox primeiro!")
    cid = database.create_clan(name, ctx.author.id)
    if cid:
        database.add_clan_member(cid, ctx.author.id, gt)
        await ctx.send(f"✅ Clã **{name}** criado!")
    else:
        await ctx.send("❌ Esse nome já existe.")


@clan.command(name="convidar")
async def clan_convidar(ctx, member: discord.Member):
    clan_info = database.get_clan_by_leader(ctx.author.id)
    if not clan_info:
        return await ctx.send("❌ Apenas líderes podem convidar.")
    if database.create_clan_invite(clan_info["id"], member.id):
        await ctx.send(
            f"📩 {member.mention}, você foi convidado para o clã **{clan_info['name']}**!"
        )
    else:
        await ctx.send("❌ Erro ou convite já enviado.")


@clan.command(name="aceitar")
async def clan_aceitar(ctx):
    invites = database.get_pending_invites(ctx.author.id)
    if not invites:
        return await ctx.send("❌ Nenhum convite pendente.")
    invite = invites[0]
    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send("❌ Vincule seu Xbox primeiro!")
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
    print(f"Bot pronto: {bot.user}")


async def main():
    async with bot:
        database.init_db()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
