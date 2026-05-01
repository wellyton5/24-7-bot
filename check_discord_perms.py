import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1473149803167748311


async def check_permissions():
    client = discord.Client(intents=discord.Intents.all())

    @client.event
    async def on_ready():
        print(f"Bot logado as {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} nao encontrado.")
            await client.close()
            return

        print(f"--- PERMISSOES DE OVERRIDE EM #{channel.name} ---")
        for target, overwrite in channel.overwrites.items():
            print(
                f"Target: {target} ({'Cargo' if isinstance(target, discord.Role) else 'Membro'})"
            )
            # Mostrar os estados das permissões de visualizar
            allow, deny = overwrite.pair()
            print(
                f"  View Channel: {'Allow' if allow.view_channel else 'Deny' if deny.view_channel else 'Inherit'}"
            )
            print(
                f"  Read History: {'Allow' if allow.read_message_history else 'Deny' if deny.read_message_history else 'Inherit'}"
            )

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(check_permissions())
