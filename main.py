import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import subprocess
# Carga las variables de entorno
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("No se encontró el token en .env")

# Configuración de intents específicos
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def load_extensions():
    try:
        await bot.load_extension('cogs.music')
        print("✅ Extensión de música cargada correctamente")
    except Exception as e:
        print(f"❌ Error al cargar la extensión de música: {e}")

@bot.event
async def on_ready():
    print(f'\n✅ {bot.user} ha iniciado sesión!')
    print(f'🆔 ID: {bot.user.id}')
    print(f'📡 Conectado a {len(bot.guilds)} servidores\n')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="!help"
    ))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("⚠️ Comando no encontrado. Usa `!help` para ver la lista.")
    else:
        print(f"Error en comando {ctx.command}: {error}")

async def main():
    await load_extensions()
    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        print("❌ Error de autenticación: Token inválido")
    except KeyboardInterrupt:
        print("\n🔌 Bot desconectado manualmente")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == '__main__':
    from keep_alive import keep_alive
    keep_alive()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Programa terminado")