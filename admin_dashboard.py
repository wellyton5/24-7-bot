import discord
import discord.ui as ui
import os
import subprocess
import ftp_helpers
import database
import json
import logging

logger = logging.getLogger("bot247")


def get_vps_status():
    try:
        # Tenta pegar info do linux
        uptime = subprocess.check_output("uptime -p", shell=True, text=True).strip()
        free_m = subprocess.check_output(
            "free -h | grep Mem", shell=True, text=True
        ).strip()
        return f"**Uptime:** {uptime}\n**Memória (Free):** {free_m}"
    except Exception:
        return "Disponível apenas em ambiente Linux."


# ==========================================
# 📋 MODALS (Popups de Entrada de Dados)
# ==========================================


class UnbanModal(ui.Modal, title="Desbanir Jogador Expresso"):
    gamertag = ui.TextInput(
        label="Gamertag a Desbanir",
        placeholder="Digite a gamertag exata",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gt = self.gamertag.value.strip()

        # 1. Remover do Banco de Dados
        conn = database._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT xuid FROM infractions WHERE gamertag = ?", (gt,))
        rows = cur.fetchall()
        cur.execute("DELETE FROM infractions WHERE gamertag = ?", (gt,))
        conn.commit()
        conn.close()

        # 2. Remover do FTP (ban.txt)
        removed = False
        try:
            ftp = ftp_helpers.connect_ftp()
            if ftp:
                ban_path = "/dayzxb/config/ban.txt"
                ban_local = "ban_temp_unban.txt"
                if ftp_helpers.download_file(ban_path, ban_local):
                    with open(ban_local, "r") as f:
                        lines = f.readlines()

                    new_lines = []
                    for line in lines:
                        # Se achou qualquer um dos XUIDs banidos pelo nome, remove
                        delete_this = False
                        for r in rows:
                            if r[0] and r[0] in line:
                                delete_this = True
                                removed = True
                                break
                        if not delete_this and line.strip():
                            new_lines.append(line)

                    with open(ban_local, "w") as f:
                        for nl in new_lines:
                            f.write(nl if nl.endswith("\n") else nl + "\n")

                    ftp_helpers.upload_file(ban_local, ban_path)
                    os.remove(ban_local)
                ftp.quit()
        except Exception as e:
            logger.error(f"Erro no unban FTP: {e}")

        # Se não excluiu do FTP diretamente pelo XUID, e se tivéssemos só o nome?
        # É complexo se não tivermos o XUID salvo, mas pelo menos limpou o BD.
        msg = f"✅ Jogador **{gt}** desbanido do Banco de Dados."
        if removed:
            msg += "\n✅ Removido fisicamente do `ban.txt` no servidor."
        else:
            msg += "\n⚠️ Não foi possível confirmar a remoção no `ban.txt` (XUID não encontrado no arquivo ou sem registro)."

        await interaction.followup.send(msg, ephemeral=True)


class PlayerInfoModal(ui.Modal, title="Ficha Criminal / Info do Player"):
    gamertag = ui.TextInput(label="Gamertag", placeholder="Ex: Player1", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        gt = self.gamertag.value.strip()
        conn = database._get_conn()
        cur = conn.cursor()

        # In infractions
        cur.execute(
            "SELECT infraction_type, description, evidence, timestamp FROM infractions WHERE gamertag = ?",
            (gt,),
        )
        infractions = cur.fetchall()

        # In Identities
        cur.execute(
            "SELECT xuid, last_ip, last_seen FROM player_identities WHERE gamertag = ?",
            (gt,),
        )
        identity = cur.fetchone()

        # In Bases
        cur.execute("SELECT id FROM bases_security WHERE owner_gamertag = ?", (gt,))
        bases = cur.fetchall()

        # In Clans
        cur.execute(
            "SELECT clan_id, role, joined_at FROM clan_members_247 WHERE gamertag = ?",
            (gt,),
        )
        clan = cur.fetchone()
        conn.close()

        res = f"**Ficha de:** `{gt}`\n\n"
        if identity:
            res += f"**XUID:** {identity[0]}\n**IP:** {identity[1]}\n**Visto em:** {identity[2]}\n\n"
        else:
            res += "🕵️ Sem registro de identidade/radar ainda.\n\n"

        if clan:
            res += f"🛡️ **Clã:** ID {clan[0]} ({clan[1]}) desde {clan[2]}\n"

        if bases:
            res += f"⛺ **Bases Registradas:** {len(bases)}\n"

        if infractions:
            res += f"🚨 **Infrações ({len(infractions)}):**\n"
            import re

            for inf in infractions[-5:]:
                type_ = inf[0]
                desc_raw = str(inf[1]) if inf[1] else ""
                evidence_raw = str(inf[2]) if inf[2] else ""

                detalhe = ""
                if type_ == "glitch_abuse" and "Emote" in evidence_raw:
                    # Extrai qual emote foi do evidence "(id=... pos=...) performed EmoteShrug)"
                    m = re.search(r"performed (Emote\w+)", evidence_raw)
                    if m:
                        detalhe = f"*{m.group(1)}*"
                    elif "Glitched/Rápida" in desc_raw:
                        detalhe = f"*{desc_raw}*"
                elif type_ == "territory_invasion":
                    # Extrai o nome do dono da base que ele invadiu
                    m = re.search(r"area de (.+)", desc_raw)
                    if m:
                        detalhe = f"*Invadiu Base de {m.group(1).strip()}*"
                    else:
                        detalhe = f"*{desc_raw}*"
                else:
                    detalhe = f"*{desc_raw[:50]}*"

                desc_final = f" - {detalhe}" if detalhe else ""
                res += f" - **{type_}** ({inf[3]}){desc_final}\n"
        else:
            res += "✅ Nenhuma infração."

        await interaction.response.send_message(res, ephemeral=True)


class GlobalAnnouncementModal(ui.Modal, title="Anúncio Global"):
    titulo = ui.TextInput(
        label="Título do Anúncio", placeholder="Atenção Jogadores", required=True
    )
    mensagem = ui.TextInput(
        label="Mensagem", style=discord.TextStyle.paragraph, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Manda no canal de rules ou avisos (assumindo que seja o de regras ou geral)
        channel_id = os.getenv("RULES_CHANNEL_ID")
        if not channel_id:
            await interaction.response.send_message(
                "Canal de regras não configurado no .env.", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(int(channel_id))
        if channel:
            embed = discord.Embed(
                title=self.titulo.value,
                description=self.mensagem.value,
                color=discord.Color.red(),
            )
            embed.set_footer(
                text=f"Anúncio feito por {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )
            await channel.send("@everyone", embed=embed)
            await interaction.response.send_message(
                "Anúncio enviado com sucesso!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Não consegui encontrar o canal.", ephemeral=True
            )


class DeleteClanModal(ui.Modal, title="Deletar Clã / Região"):
    clan_name = ui.TextInput(
        label="Nome exato do Clã a Deletar",
        placeholder="Ex: OS EXILADOS",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cname = self.clan_name.value.strip()
        conn = database._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM clans_247 WHERE name = ?", (cname,))
        row = cur.fetchone()
        if row:
            cid = row[0]
            cur.execute("DELETE FROM clan_invites_247 WHERE clan_id = ?", (cid,))
            cur.execute("DELETE FROM clan_members_247 WHERE clan_id = ?", (cid,))
            cur.execute("DELETE FROM clans_247 WHERE id = ?", (cid,))
            conn.commit()
            await interaction.followup.send(
                f"🗑️ Clã **{cname}** e todos os seus membros deletados do sistema.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"❌ Clã **{cname}** não encontrado.", ephemeral=True
            )
        conn.close()


# ==========================================
# 🎛️ PAINEL PRINCIPAL (View)
# ==========================================


class AdminDashboardView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistente

    # --- FILEIRA 1: Consultas Expressas (Row 0) ---

    @ui.button(
        label="Status VPS",
        style=discord.ButtonStyle.primary,
        custom_id="admin_status_vps",
        emoji="📊",
        row=0,
    )
    async def btn_status(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        conn = database._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM clans_247")
        clans_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM bases_security")
        bases_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM infractions")
        bans_count = cur.fetchone()[0]
        conn.close()

        vps_info = get_vps_status()

        msg = (
            f"**⚙️ Relatório do Servidor**\n\n"
            f"{vps_info}\n\n"
            f"**📦 Banco de Dados:**\n"
            f"- Clãs Registrados: `{clans_count}`\n"
            f"- Bases Protegidas: `{bases_count}`\n"
            f"- Bans Registrados: `{bans_count}`\n"
        )
        await interaction.followup.send(msg, ephemeral=True)

    @ui.button(
        label="Últimos Bans",
        style=discord.ButtonStyle.primary,
        custom_id="admin_latest_bans",
        emoji="🚨",
        row=0,
    )
    async def btn_bans(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        conn = database._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT gamertag, infraction_type, timestamp FROM infractions ORDER BY id DESC LIMIT 10"
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            await interaction.followup.send(
                "Sem banimentos recentes no Banco de Dados.", ephemeral=True
            )
            return

        msg = "**🚨 Últimos 10 Banimentos:**\n"
        for r in rows:
            msg += f"- **{r[0]}**: {r[1]} (*{r[2]}*)\n"

        await interaction.followup.send(msg, ephemeral=True)

    @ui.button(
        label="Radar Atual",
        style=discord.ButtonStyle.primary,
        custom_id="admin_radar",
        emoji="📍",
        row=0,
    )
    async def btn_radar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        # Lê os últimos logs de conexões na TABELA de conexões de auditoria
        conn = database._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT gamertag, ip_address, timestamp FROM security_logs_247 ORDER BY id DESC LIMIT 10"
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            await interaction.followup.send(
                "Nenhum registro de radar recente no DB.", ephemeral=True
            )
            return

        msg = "**📍 Radar Simplificado (Últimos Logins DB):**\n"
        for r in rows:
            ts = str(r[2])[-8:] if r[2] else "??:??:??"
            ip = r[1] or "N/A"
            msg += f"`{ts}` | **{r[0]}** - IP: {ip}\n"

        await interaction.followup.send(msg, ephemeral=True)

    @ui.button(
        label="Clãs",
        style=discord.ButtonStyle.primary,
        custom_id="admin_list_clans",
        emoji="👥",
        row=0,
    )
    async def btn_clans(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        clans = database.get_all_clans()
        if not clans:
            await interaction.followup.send("Nenhum clã registrado.", ephemeral=True)
            return

        msg = "**🛡️ Ranking / Lista de Clãs:**\n"
        for c in clans[:20]:  # limita a 20 para não estourar o limite de msg
            msg += f"- **{c['name']}** (Líder ID: {c['leader']})\n"

        await interaction.followup.send(msg, ephemeral=True)

    # --- FILEIRA 2: Intervenção (Modals) (Row 1) ---

    @ui.button(
        label="Desbanir Jogador",
        style=discord.ButtonStyle.success,
        custom_id="admin_unban",
        emoji="🔓",
        row=1,
    )
    async def btn_unban(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(UnbanModal())

    @ui.button(
        label="Ficha Criminal",
        style=discord.ButtonStyle.success,
        custom_id="admin_player_info",
        emoji="🕵️",
        row=1,
    )
    async def btn_player_info(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.send_modal(PlayerInfoModal())

    @ui.button(
        label="Anúncio Global",
        style=discord.ButtonStyle.success,
        custom_id="admin_announce",
        emoji="📢",
        row=1,
    )
    async def btn_announce(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(GlobalAnnouncementModal())

    @ui.button(
        label="Vigiar Punidos",
        style=discord.ButtonStyle.danger,
        custom_id="admin_punished_radar",
        emoji="👁️",
        row=1,
    )
    async def btn_punished_radar(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        import sqlite3, datetime

        targets = ("GODysKING", "TERRORISTA8680", "Joca6342", "Andradus1983")
        conn = database._get_conn()
        cur = conn.cursor()

        placeholders = ", ".join(["?"] * len(targets))
        query = f"SELECT gamertag, last_seen FROM player_identities WHERE gamertag IN ({placeholders})"
        cur.execute(query, targets)
        results = cur.fetchall()

        # Últimas Kills gerais para ver abatidos
        try:
            cur.execute(
                "SELECT killer_name, victim_name, distance, timestamp FROM killfeed ORDER BY timestamp DESC LIMIT 3"
            )
            kills = cur.fetchall()
        except:
            kills = []
        conn.close()

        agora = datetime.datetime.now()
        msg = f"**👁️ Radar Punitivo: Vigília Ativa ({agora.strftime('%H:%M')})**\n\n"

        if not results:
            msg += "Nenhum alvo cadastrado com login no DB.\n\n"
        else:
            for r in results:
                gt = r[0]
                last_seen_str = r[1]
                try:
                    dt = datetime.datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
                    minutos_atras = (agora - dt).total_seconds() / 60
                    if minutos_atras < 30:
                        msg += f"🚨 **{gt}**: LOGOU AGORA! ({int(minutos_atras)} min atrás)\n   *Possivelmente implodiu no Init.*\n"
                    else:
                        msg += f"💤 **{gt}**: Inativo (Visto há {int(minutos_atras / 60)} horas).\n"
                except:
                    msg += f"❓ **{gt}**: Visto em {last_seen_str}\n"

        msg += "\n**☠️ Últimas Mortes no Servidor:**\n"
        if kills:
            for k in kills:
                msg += f"- `{k[3][-8:]}` | {k[0]} -> {k[1]} ({k[2]}m)\n"
        else:
            msg += "- Sem mortes registradas recentemente."

        # Varrer ADM logs para Contas Novas/Alts pegas na Zona Morta
        cordon_logins = []
        try:
            ftp = ftp_helpers.connect_ftp()
            if ftp:
                import io, re, math

                cordon_zones = [
                    ("NWAF (ATC)", 4407.0, 10243.0, 450.0),
                    ("Lago Negro", 13300.0, 14300.0, 450.0),
                    ("Bunker Sz", 13285.0, 12096.0, 150.0),
                ]
                ftp.cwd("/dayzxb/config")
                items = ftp.nlst()
                adm_files = [f for f in items if f.lower().endswith(".adm")]
                if adm_files:
                    latest_adm = sorted(adm_files)[-1]
                    ftp.voidcmd("TYPE I")
                    bio = io.BytesIO()
                    ftp.retrbinary(f"RETR {latest_adm}", bio.write)
                    content = bio.getvalue().decode("utf-8", errors="ignore")

                    lines = content.splitlines()[-3000:]
                    pattern_login = r'Player "(?P<name>[^"]+)" \(id=(?P<xuid>[^ )]+) pos=<(?P<coords>[^>]+)>\)'

                    for line in lines:
                        if "connected" in line.lower():
                            m = re.search(pattern_login, line)
                            if m:
                                p_name = m.group("name")
                                coords_str = m.group("coords")
                                parts = coords_str.split(",")
                                if len(parts) >= 2:
                                    try:
                                        x, z = (
                                            float(parts[0]),
                                            float(
                                                parts[2] if len(parts) > 2 else parts[1]
                                            ),
                                        )
                                        for z_name, cx, cz, rad in cordon_zones:
                                            dist = math.hypot(x - cx, z - cz)
                                            if dist <= rad:
                                                cordon_logins.append(
                                                    f"⚠️ **{p_name}** | {z_name} (Dist: {int(dist)}m)"
                                                )
                                    except:
                                        pass
                ftp.quit()
        except:
            cordon_logins.append("(Erro FTP)")

        msg += "\n\n**🚷 Alts Mortas nas Zonas (Logs da Sessão):**\n"
        if cordon_logins and "(Erro FTP)" not in cordon_logins:
            msg += "\n".join(set(cordon_logins[-5:])) + "\n"
        elif "(Erro FTP)" in cordon_logins:
            msg += "- Erro ao conectar ao FTP.\n"
        else:
            msg += "- Ninguém novo (Limpo por enquanto).\n"

        await interaction.followup.send(msg, ephemeral=True)

    # --- FILEIRA 3: Nuvem e Emergências (Row 2) ---

    @ui.button(
        label="Ligar/Desligar Free Build",
        style=discord.ButtonStyle.danger,
        custom_id="admin_toggle_raid",
        emoji="🟢",
        row=2,
    )
    async def btn_toggle_raid(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        await interaction.response.defer(ephemeral=True)
        # Vamos usar o helper existente no ftp ou baixar o cfg
        LOCAL_CFG = os.getenv("LOCAL_GAMEPLAY_CONFIG", "cfggameplay_temp.json")
        GAMEPLAY_CONFIG_PATH = os.getenv(
            "GAMEPLAY_CONFIG_PATH",
            "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json",
        )
        try:
            ftp = ftp_helpers.connect_ftp()
            if not ftp:
                return await interaction.followup.send(
                    "Erro: Não foi possível conectar ao FTP.", ephemeral=True
                )

            if ftp_helpers.download_file(GAMEPLAY_CONFIG_PATH, LOCAL_CFG):
                with open(LOCAL_CFG, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Toggle all 11 keys
                current_state = (
                    data.get("BaseBuildingData", {})
                    .get("HologramData", {})
                    .get("disableIsCollidingBBoxCheck", False)
                )
                new_state = not current_state

                hologram_data = data.setdefault("BaseBuildingData", {}).setdefault(
                    "HologramData", {}
                )

                keys_to_toggle = [
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

                for key in keys_to_toggle:
                    hologram_data[key] = new_state

                with open(LOCAL_CFG, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

                ftp_helpers.upload_file(LOCAL_CFG, GAMEPLAY_CONFIG_PATH)
                os.remove(LOCAL_CFG)

                status_txt = (
                    "ATIVADO (Pode construir livre)"
                    if new_state
                    else "DESATIVADO (Construção Restrita)"
                )
                await interaction.followup.send(
                    f"🛠️ Free Building **{status_txt}** no servidor.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Falha ao ler cfggameplay.json", ephemeral=True
                )
            ftp.quit()
        except Exception as e:
            await interaction.followup.send(
                f"Erro ao alternar modo: {e}", ephemeral=True
            )

    @ui.button(
        label="Forçar Sincronização Ban.txt",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_sync_ftp",
        emoji="🧲",
        row=2,
    )
    async def btn_sync(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        # Sincroniza XUIDs banidos do banco com ban.txt no FTP
        # O formato do ban.txt é: XUID  // comentário (uma XUID por linha)
        try:
            conn = database._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT xuid FROM infractions
                    WHERE auto_banned=1 AND ban_lifted=0
                    AND xuid IS NOT NULL AND xuid != ''
                """)
                xuids = set(r[0] for r in cur.fetchall())
            finally:
                conn.close()

            ftp = ftp_helpers.connect_ftp()
            if ftp:
                try:
                    ban_path = "/dayzxb/config/ban.txt"
                    ban_local = "ban_sync.txt"
                    ftp_helpers.download_file(ban_path, ban_local)

                    existing = set()
                    if os.path.exists(ban_local):
                        with open(ban_local, "r") as f:
                            for line in f:
                                # O formato é: XUID  // comentário
                                stripped = line.strip()
                                if stripped:
                                    # Pega apenas o XUID (antes de //)
                                    xuid_part = stripped.split("//")[0].strip().split()[0] if stripped else ""
                                    if xuid_part:
                                        existing.add(xuid_part)

                    missing_xuids = xuids - existing
                    if missing_xuids:
                        with open(ban_local, "a") as f:
                            for x in missing_xuids:
                                f.write(f"\n{x}  // BotSync Admin Dashboard")
                        ftp_helpers.upload_file(ban_local, ban_path)

                    if os.path.exists(ban_local):
                        os.remove(ban_local)

                    await interaction.followup.send(
                        f"🧲 Sincronização Completa! {len(missing_xuids)} bans ausentes foram forçados no `ban.txt`. Total no DB: {len(xuids)}.",
                        ephemeral=True,
                    )
                finally:
                    try:
                        ftp.quit()
                    except Exception:
                        pass
            else:
                await interaction.followup.send("Erro na conexão FTP.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                f"Erro na Sincronização: {e}", ephemeral=True
            )

    @ui.button(
        label="Excluir Clã",
        style=discord.ButtonStyle.danger,
        custom_id="admin_del_clan",
        emoji="🗑️",
        row=2,
    )
    async def btn_del_clan(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(DeleteClanModal())
