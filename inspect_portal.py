import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 867605549460881470


async def inspect_portal_channel():
    client = discord.Client(intents=discord.Intents.all())

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} não encontrado.")
            await client.close()
            return

        print(f"--- INSPEÇÃO DO CANAL DE PORTAL: #{channel.name} ---")

        # 1. Permissões
        print("\n[PERMISSÕES]")
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()
            print(f"Alvos: {target}")
            print(
                f"  View: {'Allow' if allow.view_channel else 'Deny' if deny.view_channel else 'Inherit'}"
            )
            print(
                f"  Send: {'Allow' if allow.send_messages else 'Deny' if deny.send_messages else 'Inherit'}"
            )

        # 2. Histórico
        print("\n[ÚLTIMAS MENSAGENS]")
        try:
            async for message in channel.history(limit=5):
                print(
                    f"[{message.created_at}] {message.author}: {message.content[:100]}..."
                )
                if message.components:
                    print(f"  > Componentes encontrados: {len(message.components)}")
                    for action_row in message.components:
                        for child in action_row.children:
                            if isinstance(child, discord.Button):
                                print(
                                    f"    - Botão: {child.label} (Custom ID: {child.custom_id})"
                                )
        except Exception as e:
            print(f"Erro ao ler histórico: {e}")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(inspect_portal_channel())
