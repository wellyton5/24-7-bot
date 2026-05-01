import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Carregar ambiente do bot real
load_dotenv("/home/ubuntu/24-7-Bot/.env")
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 867605549460881470


async def fix_portal_channel():
    intents = discord.Intents.all()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} não encontrado.")
            await client.close()
            return

        guild = channel.guild
        print(f"Limpando e reconfigurando: #{channel.name} ({guild.name})")

        # 1. Corrigir Permissões
        # Bot: Tudo (Allow)
        # @everyone: Ver (Allow), Falar (Deny)
        try:
            # Limpar todos os overwrites atuais para o bot para resetar
            await channel.set_permissions(
                client.user,
                view_channel=True,
                send_messages=True,
                embed_links=True,
                manage_messages=True,
            )
            await channel.set_permissions(
                guild.default_role,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            )
            print("[V] Permissões corrigidas.")
        except Exception as e:
            print(f"[X] Erro permissões: {e}")

        # 2. Limpar mensagens antigas (Faxina)
        try:
            deleted = await channel.purge(limit=100)
            print(f"[V] Removidas {len(deleted)} mensagens antigas.")
        except Exception as e:
            print(f"[X] Erro na limpeza: {e}")

        # 3. Importar e Enviar o Portal Real
        # Como o bot real já está rodando, se eu enviar o embed aqui com os custom_ids corretos, o bot real vai processar os cliques!

        embed = discord.Embed(
            title="🏆 Portal de Clãs e Cadastro - Brasil Sul",
            description=(
                "Bem-vindo ao sistema de soberania do servidor!\n\n"
                "**COMO FUNCIONA:**\n"
                "1️⃣ Clique no botão **Azul** para vincular seu Gamertag ao Discord.\n"
                "2️⃣ Clique no botão **Verde** se desejar registrar um novo clã.\n"
                "3️⃣ Use os botões de gerenciamento se você for um líder.\n\n"
                "⚠️ *O vínculo é obrigatório para participar da economia e eventos do servidor.*"
            ),
            color=0x2B2D31,
        )

        # Botões com os IDs que o main_24-7.py reconhece
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                label="🔗 Vincular Gamertag",
                style=discord.ButtonStyle.blurple,
                custom_id="portal:link_gamertag",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="🚩 Registrar Meu Clã",
                style=discord.ButtonStyle.success,
                custom_id="portal:create_clan",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="➕ Adicionar Membro",
                style=discord.ButtonStyle.primary,
                custom_id="portal:add_member",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="📩 Aceitar Convite",
                style=discord.ButtonStyle.secondary,
                custom_id="portal:accept_invite",
            )
        )

        await channel.send(embed=embed, view=view)
        print("[V] Novo Portal enviado com sucesso.")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(fix_portal_channel())
