import discord
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID"))

client = discord.Client(intents=discord.Intents.default())


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    for guild in client.guilds:
        print(f"\nGuild: {guild.name} (ID: {guild.id})")

        me = guild.me
        print(
            f"Bot Highest Role: {me.top_role.name} (Position: {me.top_role.position})"
        )

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        if verified_role:
            print(
                f"Verified Role: {verified_role.name} (Position: {verified_role.position})"
            )

            if me.top_role.position > verified_role.position:
                print("✅ Bot is ABOVE Verified Role.")
            else:
                print("❌ Bot is BELOW Verified Role.")
                print(
                    "Manual Action Required: Move the bot's role UP in the Discord Server Settings."
                )
        else:
            print("❌ Verified Role not found in this guild.")

    await client.close()


client.run(TOKEN)
