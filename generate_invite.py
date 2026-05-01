import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1473149803167748311


async def create_permanent_invite():
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} não encontrado.")
            await client.close()
            return

        try:
            # Criar convite permanente (max_age=0, max_uses=0)
            invite = await channel.create_invite(
                max_age=0,
                max_uses=0,
                unique=False,
                reason="Link permanente solicitado pelo Administrador para compartilhamento.",
            )
            print(f"SUCESSO_LINK: {invite.url}")
        except Exception as e:
            print(f"Erro ao criar convite: {e}")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(create_permanent_invite())
