import discord
from discord.ext import commands

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="ping", description="Check if Dropwatch is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Dropwatch is online!")

bot.run("YOUR_BOT_TOKEN")
