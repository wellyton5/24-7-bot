import os
import discord
import asyncio
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1473149803167748311
GUILD_ID = 865075947572953159


async def make_channel_public():
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} não encontrado.")
            await client.close()
            return

        guild = channel.guild
        print(f"Canal encontrado: #{channel.name} no servidor {guild.name}")

        try:
            # Definir permissão de ver canal para @everyone como True
            await channel.set_permissions(guild.default_role, view_channel=True)
            print(f"Sucesso! O canal #{channel.name} agora está público.")
        except Exception as e:
            print(f"Erro ao alterar permissões: {e}")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro ao conectar ao Discord: {e}")


if __name__ == "__main__":
    asyncio.run(make_channel_public())
