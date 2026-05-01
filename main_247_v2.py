import asyncio
import io
import json
import os
import re
import math
import requests
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import database
from ftp_helpers import connect_ftp, download_file, upload_file
import discord.ui as ui

# --- CONFIGURAÇÃO ---
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
NITRADO_TOKEN = os.getenv("NITRADO_TOKEN")
SERVICE_ID = os.getenv("SERVICE_ID")
BAN_CHANNEL_ID = os.getenv("BAN_CHANNEL")
VERIFIED_ROLE_ID = os.getenv("VERIFIED_ROLE_ID")
PORTAL_CHANNEL_ID = os.getenv("PORTAL_CHANNEL_ID")
RADAR_WEBHOOK_URL = os.getenv("RADAR_WEBHOOK_URL")
RULES_CHANNEL_ID = os.getenv("RULES_CHANNEL_ID", "1384330092586729472")

# Caminhos Nitrado
GAMEPLAY_CONFIG_PATH = "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json"
LOCAL_GAMEPLAY_CONFIG = "cfggameplay_temp.json"

# Estado Global do Monitor
current_log_file = None
last_byte_offset = 0
_log_check_counter = 0
_player_id_cache = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
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


# --- HELPERS ---


def _is_garden(item_name):
    return "GardenPlot" in item_name


def _is_fireplace(item_name):
    return "Fireplace" in item_name


def _is_garden_or_fireplace(item_name):
    return _is_garden(item_name) or _is_fireplace(item_name)


async def restart_nitrado():
    if not NITRADO_TOKEN or not SERVICE_ID:
        print("[NITRADO] Erro: Credenciais ausentes no .env")
        return False
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/restart"
    headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
    try:
        response = requests.post(url, headers=headers)
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


# --- COMANDOS DE JOGADOR ---


@bot.command(name="vincular")
async def vincular(ctx, gamertag: str):
    """Vincula o Discord do jogador ao seu Gamertag no Bot 24/7."""
    database.add_clan_member(0, ctx.author.id, gamertag)
    await ctx.send(
        f"✅ **{ctx.author.display_name}**, seu Gamertag **{gamertag}** foi vinculado com sucesso!"
    )


@bot.group(name="clan", invoke_without_command=True)
async def clan(ctx):
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
    """Lista todos os clãs registrados no servidor."""
    clans = database.get_all_clans()
    if not clans:
        return await ctx.send("📭 Nenhum clã registrado ainda.")

    msg = "🏆 **Clãs Registrados:**\n"
    for c in clans:
        leader = ctx.guild.get_member(int(c["leader"]))
        leader_name = leader.display_name if leader else "Desconhecido"
        msg += f"• **{c['name']}** (Líder: {leader_name})\n"

    await ctx.send(msg)


@clan.command(name="aceitar")
async def clan_aceitar(ctx):
    """Aceita um convite de clã pendente."""
    invites = database.get_pending_invites(ctx.author.id)
    if not invites:
        return await ctx.send("❌ Você não tem convites pendentes.")

    # Se tiver mais de um, pega o mais recente ou o primeiro
    invite = invites[0]
    clan_name = invite["clan_name"]

    gt = database.get_gamertag_by_discord(ctx.author.id)
    if not gt:
        return await ctx.send(
            "❌ Você precisa usar `!vincular <gamertag>` antes de aceitar o convite."
        )

    database.add_clan_member(invite["clan_id"], ctx.author.id, gt)
    database.delete_invite(invite["id"])

    await ctx.send(f"🎉 Bem-vindo ao clã **{clan_name}**, {ctx.author.mention}!")

    # Log Admin
    await notify_admin_log(
        f"🤝 **Membro Adicionado**: {ctx.author.display_name} ({gt}) entrou no clã **{clan_name}**."
    )


@clan.command(name="recusar")
async def clan_recusar(ctx):
    """Recusa convites de clã pendentes."""
    invites = database.get_pending_invites(ctx.author.id)
    if not invites:
        return await ctx.send("❌ Você não tem convites pendentes.")

    for invite in invites:
        database.delete_invite(invite["id"])

    await ctx.send("✅ Todos os convites foram recusados.")


@clan.command(name="criar")
async def clan_criar(ctx, *, name: str):
    if database.get_clan_by_leader(ctx.author.id):
        return await ctx.send("❌ Você já é líder de um clã!")

    clan_id = database.create_clan(name, ctx.author.id)
    if clan_id:
        gt = database.get_gamertag_by_discord(ctx.author.id)
        database.add_clan_member(clan_id, ctx.author.id, gt)
        await ctx.send(f"✅ Clã **{name}** criado com sucesso!")
        await notify_admin_log(
            f"🚩 **Novo Clã**: {ctx.author.display_name} criou o clã **{name}**."
        )
    else:
        await ctx.send("❌ Esse nome de clã já existe.")


@clan.command(name="convidar")
async def clan_convidar(ctx, member: discord.Member):
    clan_info = database.get_clan_by_leader(ctx.author.id)
    if not clan_info:
        return await ctx.send("❌ Apenas o líder do clã pode convidar membros.")

    gt = database.get_gamertag_by_discord(member.id)
    if not gt:
        return await ctx.send(
            f"❌ {member.mention} precisa usar `!vincular <gamertag>` primeiro."
        )

    if database.create_clan_invite(clan_info["id"], member.id):
        await ctx.send(
            f"📩 {member.mention}, você foi convidado para o clã **{clan_info['name']}**!\nUse `!clan aceitar` para entrar."
        )
    else:
        await ctx.send(
            "❌ Não foi possível enviar o convite (talvez já exista um convite pendente)."
        )


# --- PORTAL INTERATIVO (BOTÕES/JANELAS) ---


class LinkGTModal(ui.Modal, title="🔗 Vincular Gamertag"):
    gamertag = ui.TextInput(
        label="Sua Gamertag (Xbox)",
        placeholder="Ex: XxPlayerOneXx",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        database.add_clan_member(0, interaction.user.id, self.gamertag.value)

        # Atribuição de Cargo Opcional (Silent Mode)
        if VERIFIED_ROLE_ID:
            try:
                role = interaction.guild.get_role(int(VERIFIED_ROLE_ID))
                if role:
                    await interaction.user.add_roles(role)
            except Exception as e:
                print(f"[GATEKEEPING ERROR] Não consegui atribuir o cargo: {e}")

        await interaction.response.send_message(
            f"✅ **Registro Concluído!** Olá **{interaction.user.display_name}**, sua Gamertag `{self.gamertag.value}` já está vinculada e liberada no servidor da Nitrado.",
            ephemeral=True,
        )


class CreateClanModal(ui.Modal, title="🚩 Registrar Novo Clã"):
    clan_name = ui.TextInput(
        label="Nome do Clã",
        placeholder="Ex: Os Justiceiros",
        min_length=3,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if database.get_clan_by_leader(interaction.user.id):
            return await interaction.response.send_message(
                "❌ Você já é líder de um clã!", ephemeral=True
            )

        clan_id = database.create_clan(self.clan_name.value, interaction.user.id)
        if clan_id:
            gt = database.get_gamertag_by_discord(interaction.user.id)
            database.add_clan_member(clan_id, interaction.user.id, gt)
            await interaction.response.send_message(
                f"✅ Clã **{self.clan_name.value}** criado!", ephemeral=True
            )
            await notify_admin_log(
                f"🚩 **Novo Clã**: {interaction.user.display_name} criou **{self.clan_name.value}** via Portal."
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


class ClanPortalView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="🔗 Vincular Gamertag",
        style=discord.ButtonStyle.primary,
        custom_id="portal:link_gt",
    )
    async def link_gt(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LinkGTModal())

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
        label="📩 Aceitar Convite",
        style=discord.ButtonStyle.secondary,
        custom_id="portal:accept_invite",
    )
    async def accept_invite(self, interaction: discord.Interaction, button: ui.Button):
        invites = database.get_pending_invites(interaction.user.id)
        if not invites:
            return await interaction.response.send_message(
                "❌ Nenhum convite pendente.", ephemeral=True
            )

        invite = invites[0]
        gt = database.get_gamertag_by_discord(interaction.user.id)
        if not gt:
            return await interaction.response.send_message(
                "❌ Vincule sua Gamertag primeiro!", ephemeral=True
            )

        database.add_clan_member(invite["clan_id"], interaction.user.id, gt)
        database.delete_invite(invite["id"])
        await interaction.response.send_message(
            f"🎉 Bem-vindo ao clã **{invite['clan_name']}**!", ephemeral=True
        )
        await notify_admin_log(
            f"🤝 **Membro Adicionado**: {interaction.user.display_name} entrou no clã **{invite['clan_name']}** via Portal."
        )

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


@bot.command(name="portal")
@commands.has_permissions(administrator=True)
async def portal_setup(ctx):
    """Cria e configura o portal interativo em 'Modo Fantasma'."""
    # Configuração de Permissões Automática (Ghost Mode)
    # Bloqueia @everyone de ver qualquer coisa além desta mensagem e do Bot
    everyone = ctx.guild.default_role

    # Permissões do Canal
    overwrites = {
        everyone: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=False,
        ),
        ctx.guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, embed_links=True
        ),
    }

    # Aplica no canal atual
    await ctx.channel.edit(overwrites=overwrites)

    embed = discord.Embed(
        title="🏆 Portal de Clãs - 24/7 Security",
        description=(
            "Bem-vindo ao centro de gestão de clãs!\n\n"
            "**1.** Use o botão azul para vincular seu Xbox.\n"
            "**2.** Use o botão verde para registrar seu clã.\n"
            "**3.** Use o botão azul (Adicionar) para cadastrar os Gamertags de seus amigos no seu clã.\n"
            "**4.** Use o botão cinza para aceitar convites pendentes.\n"
            "**5.** Use o botão vermelho para **CANCELAR REGISTROS** e apagar seu clã atual.\n\n"
            "*Líderes: Ao adicionar o Gamertag de um amigo, ele é automaticamente autorizado em suas bases e não será banido pelo Radar.*"
        ),
        color=discord.Color.gold(),
    )

    await ctx.send(embed=embed, view=ClanPortalView())
    await ctx.send(
        "✅ **Modo Fantasma Ativado!** Este canal foi configurado para privacidade total.",
        delete_after=5,
    )
    await ctx.message.delete()


@bot.group(name="base", invoke_without_command=True)
async def base(ctx):
    await ctx.send(
        "🏰 **Comandos de Base:**\n`!base autorizar @amigo` - Autoriza um amigo na sua base\n`!base remover @amigo` - Remove autorização"
    )


@base.command(name="autorizar")
async def base_autorizar(ctx, member: discord.Member):
    bases = database.get_security_bases()
    author_gt = database.get_gamertag_by_discord(ctx.author.id)
    owned_bases = [
        b
        for b in bases
        if b["owner_discord_id"] == str(ctx.author.id) or b["owner"] == author_gt
    ]

    if not owned_bases:
        return await ctx.send("❌ Você não é proprietário de nenhuma base registrada.")

    guest_gt = database.get_gamertag_by_discord(member.id)
    if not guest_gt:
        return await ctx.send(
            f"❌ O jogador {member.mention} precisa usar `!vincular` primeiro."
        )

    for b in owned_bases:
        database.authorize_guest(b["id"], guest_gt, ctx.author.id)

    await ctx.send(f"✅ {member.mention} ({guest_gt}) foi autorizado em suas bases!")


# --- LOG PARSER & LOGIC ---


async def parse_log_line(line):
    line = line.strip()
    if not line or "pos=<" not in line:
        return

    try:
        player_name = line.split('Player "')[1].split('"')[0]
        coords = line.split("pos=<")[1].split(">")[0].split(",")
        x, z = float(coords[0]), float(coords[2])

        if "id=" in line:
            p_xuid = line.split("id=")[1].split(" ")[0].strip()
            _player_id_cache[player_name] = p_xuid
            database.update_player_identity(player_name, p_xuid)

        action_line = line.split(">")[1].strip() if ">" in line else ""
        action_line_lower = action_line.lower()

        # 1. DETECÇÃO DE CONSTRUÇÃO (built)
        if "built" in action_line_lower:
            base = database.get_base_at(x, z)
            if not base:
                # Registro Automático na primeira parede construída
                if any(k in action_line_lower for k in ["fence", "gate", "watchtower"]):
                    # O database.register_new_base já busca o discord_id se necessário
                    database.register_new_base(player_name, x, z)
                    print(f"[BASE REGISTERED] {player_name} em {x}, {z}")
                    msg = f"🏰 **SOBERANIA REGISTRADA**\nO jogador **{player_name}** construiu sua primeira estrutura e assumiu a soberania em **[{int(x)}, {int(z)}]**.\nÁrea protegida em 50m!"
                    await notify_ban(msg)
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
                    from auto_ban_system import ban_player_immediate

                    ban_player_immediate(
                        player_name,
                        _player_id_cache.get(player_name),
                        f"Construindo em base de {base['owner']}",
                        "territory_invasion",
                    )

        # 2. DETECÇÃO DE COLOCAÇÃO DE ITENS (placed)
        elif "placed" in action_line_lower:
            parts = re.split(r"placed\s+", action_line, flags=re.IGNORECASE)
            item_name = parts[1].split("<")[0].strip() if len(parts) > 1 else "item"

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
                # Limite global fora de base
                database.increment_item_count(player_name, item_name)
                count = database.get_item_count(player_name, item_name)
                if count > 2:
                    msg = f"🚫 **BANIMENTO POR LIMITE**\nO jogador **{player_name}** excedeu o limite global de fogueiras/plantações! Item: **{item_name}**"
                    await notify_ban(msg)
                    from auto_ban_system import ban_player_immediate

                    ban_player_immediate(
                        player_name,
                        _player_id_cache.get(player_name),
                        f"Excesso de {item_name} fora de base",
                        "garden_exploit",
                    )

        # 3. DETECÇÃO DE RADAR / DISMANTLE
        elif "dismantled" in action_line_lower:
            parts = re.split(r"dismantled\s+", action_line, flags=re.IGNORECASE)
            item_name = parts[1].split(" (")[0].strip() if len(parts) > 1 else "item"

            base = database.get_base_at(x, z)
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
                    from auto_ban_system import ban_player_immediate

                    ban_player_immediate(
                        player_name,
                        _player_id_cache.get(player_name),
                        f"Raid em Base Protegida: Desmontando {item_name}",
                        "raid_exploit",
                    )
    except Exception as e:
        print(f"[PARSE ERROR] {e}")


# --- TASKS & INIT ---


@tasks.loop(seconds=60)
async def raid_scheduler():
    br_now = datetime.now(timezone.utc) - timedelta(hours=3)
    if br_now.weekday() == 5:
        if br_now.hour == 20 and br_now.minute == 0:
            if download_file(GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG):
                try:
                    with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
                        config = json.load(f)
                    config["GeneralData"]["disableBaseDamage"] = False
                    with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
                        json.dump(config, f, indent=4)
                    if upload_file(LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH):
                        await restart_nitrado()
                        await notify_ban(
                            "🔥 **RAID INICIADO!** Dano em bases liberado até as 22:00!"
                        )
                except Exception:
                    pass
        elif br_now.hour == 22 and br_now.minute == 0:
            if download_file(GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG):
                try:
                    with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
                        config = json.load(f)
                    config["GeneralData"]["disableBaseDamage"] = True
                    with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
                        json.dump(config, f, indent=4)
                    if upload_file(LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH):
                        await restart_nitrado()
                        await notify_ban(
                            "🛑 **RAID ENCERRADO!** Dano em bases bloqueado!"
                        )
                except Exception:
                    pass


async def notify_ban(message):
    print(f"[NOTIFY] {message}")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(webhook_url, json={"content": message}, timeout=5)
        except Exception:
            pass


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


async def notify_admin_log(message):
    """Envia logs de auditoria para o canal administrativo."""
    print(f"[ADMIN LOG] {message}")
    channel = bot.get_channel(
        int(BAN_CHANNEL_ID)
    )  # Usando o canal de ban para logs por enquanto
    if channel:
        try:
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


@tasks.loop(seconds=15)
async def monitor_logs():
    global last_byte_offset, current_log_file
    ftp = connect_ftp()
    if not ftp:
        return
    try:
        if not current_log_file:
            current_log_file = find_latest_adm_log(ftp)
            if current_log_file:
                ftp.voidcmd("TYPE I")
                last_byte_offset = ftp.size(current_log_file)

        if current_log_file:
            ftp.voidcmd("TYPE I")
            server_size = ftp.size(current_log_file)
            if server_size > last_byte_offset:
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
        print(f"[MONITOR ERROR] {e}")
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def find_latest_adm_log(ftp):
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            ftp.voidcmd("TYPE I")
            items = ftp.nlst()
            adm_files = [f"{path}/{f}" for f in items if f.lower().endswith(".adm")]
            if adm_files:
                return sorted(adm_files)[-1]
        except Exception:
            continue
    return None


@bot.event
async def on_ready():
    print(f"[EVENT] Bot ready: {bot.user}")
    bot.add_view(ClanPortalView())  # Mantém os botões funcionando após reiniciar

    # Configuração de Canal e Envio do Portal Automático
    if PORTAL_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(PORTAL_CHANNEL_ID))
            if channel:
                # Limpa mensagens antigas do próprio bot para manter o canal limpo (opcional)
                async for message in channel.history(limit=10):
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
                    f"🚀 **Bot Reiniciado**: Portal atualizado no canal."
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
                        "Rams e invasões técnicas foram liberadas pois o servidor possui **Radar Ativo**.\n\n"
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

    if not monitor_logs.is_running():
        monitor_logs.start()
    if not raid_scheduler.is_running():
        raid_scheduler.start()


async def main():
    async with bot:
        database.init_db()
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
