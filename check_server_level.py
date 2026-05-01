import os
import discord
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 865075947572953159


async def check_server_level():
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        print(f"Bot logado como {client.user}")
        guild = client.get_guild(GUILD_ID)

        if not guild:
            print(f"Erro: Servidor {GUILD_ID} não encontrado.")
            await client.close()
            return

        print(f"--- STATUS DO SERVIDOR: {guild.name} ---")
        print(f"Nível de Boost: {guild.premium_tier}")
        print(f"Número de Boosts: {guild.premium_subscription_count}")
        print(f"Vanity URL: {guild.vanity_url_code or 'Não definida'}")

        features = guild.features
        print(f"Recursos disponíveis: {features}")

        if "VANITY_URL" in features:
            print("O servidor PODE ter link personalizado!")
        else:
            print("O servidor NÃO tem nível suficiente para link personalizado nativo.")

        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    asyncio.run(check_server_level())
