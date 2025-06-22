import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables del .env

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'  # Ejemplo de otra configuración