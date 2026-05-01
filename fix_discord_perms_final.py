import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1473149803167748311


async def fix_perms_final():
    client = discord.Client(intents=discord.Intents.all())

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        channel = client.get_channel(CHANNEL_ID)

        if not channel:
            print(f"Erro: Canal {CHANNEL_ID} não encontrado.")
            await client.close()
            return

        guild = channel.guild
        print(f"Canal: #{channel.name} no servidor {guild.name}")

        try:
            # Garantir Visualização E Histórico para @everyone
            await channel.set_permissions(
                guild.default_role,
                view_channel=True,
                read_message_history=True,
                send_messages=False,  # Geralmente killfeed é apenas leitura para jogadores
            )
            print(
                f"Sucesso! Permissoes de visualizacao e historico ativadas para @everyone em #{channel.name}."
            )
        except Exception as e:
            print(f"Erro ao alterar permissoes: {e}")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro ao conectar ao Discord: {e}")


if __name__ == "__main__":
    asyncio.run(fix_perms_final())
