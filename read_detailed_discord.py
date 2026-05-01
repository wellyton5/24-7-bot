import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1473149803167748311


async def read_detailed_channel():
    client = discord.Client(intents=discord.Intents.all())

    @client.event
    async def on_ready():
        print(f"Bot logado as {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} encontrado.")
            await client.close()
            return

        print(f"--- LENDO DETALHES DE #{channel.name} ---")
        try:
            async for message in channel.history(limit=5):
                print(f"[{message.created_at}] {message.author}: {message.content}")
                if message.embeds:
                    for i, embed in enumerate(message.embeds):
                        print(
                            f"  Embed {i}: Title='{embed.title}', Desc='{embed.description}'"
                        )
                        if embed.fields:
                            for field in embed.fields:
                                print(f"    Field: {field.name} = {field.value}")
        except Exception as e:
            print(f"Erro: {e}")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(read_detailed_channel())
