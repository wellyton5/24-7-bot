import os
import discord
import asyncio
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1473149803167748311


async def read_channel():
    client = discord.Client(intents=discord.Intents.all())

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} não encontrado.")
            await client.close()
            return

        print(f"--- LENDO MENSAGENS DE #{channel.name} ---")
        try:
            async for message in channel.history(limit=10):
                print(f"[{message.created_at}] {message.author}: {message.content}")
                if message.attachments:
                    for att in message.attachments:
                        print(f"  > Attachment: {att.url}")
                if message.embeds:
                    for embed in message.embeds:
                        print(f"  > Embed: {embed.title or 'Sem Título'}")
        except Exception as e:
            print(f"Erro ao ler histórico: {e}")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro ao conectar ao Discord: {e}")


if __name__ == "__main__":
    asyncio.run(read_channel())
