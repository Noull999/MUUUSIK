import asyncio
from cogs.music import Music
from keep_alive import keep_alive
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carga las variables de entorno
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("No se encontró el token en .env")

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

async def load_extensions():
    await bot.load_extension('cogs.music')

@bot.event
async def on_ready():
    print(f'{bot.user} ha iniciado sesión!')

async def main():
    await load_extensions()
    await bot.start(TOKEN)  # Usa la variable directamente

if __name__ == '__main__':
    keep_alive()
    asyncio.run(main())
