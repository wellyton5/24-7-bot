import discord
from discord import ui
import os
from dotenv import load_dotenv
import database
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PORTAL_CHANNEL_ID = 867605549460881470


class ClanPortalView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="🔗 Vincular Gamertag",
        style=discord.ButtonStyle.blurple,
        custom_id="portal:link_gamertag",
    )
    async def btn1(self, i, b):
        pass

    @ui.button(
        label="🚩 Registrar Meu Clã",
        style=discord.ButtonStyle.success,
        custom_id="portal:create_clan",
    )
    async def btn2(self, i, b):
        pass

    @ui.button(
        label="➕ Adicionar Membro",
        style=discord.ButtonStyle.primary,
        custom_id="portal:add_member",
    )
    async def btn3(self, i, b):
        pass

    @ui.button(
        label="📩 Aceitar Convite",
        style=discord.ButtonStyle.secondary,
        custom_id="portal:accept_invite",
    )
    async def btn4(self, i, b):
        pass

    @ui.button(
        label="❌ CANCELAR CADASTRO",
        style=discord.ButtonStyle.danger,
        custom_id="portal:unlink_gamertag",
    )
    async def btn5(self, i, b):
        pass


async def update_portal():
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        channel = client.get_channel(PORTAL_CHANNEL_ID)
        if channel:
            async for message in channel.history(limit=50):
                if message.author.id == client.user.id and message.embeds:
                    await message.edit(view=ClanPortalView())
                    print("Portal atualizado com sucesso.")
                    break
        else:
            print(f"Canal {PORTAL_CHANNEL_ID} não encontrado.")
        await client.close()

    await client.login(TOKEN)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(update_portal())
