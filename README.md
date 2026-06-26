# 🎵 MUUUSIK

**Bot de música para Discord + Dashboard web de control**

Bot de Discord con reproducción de música desde YouTube y SoundCloud, cola de reproducción, letras de canciones, ecualizador y un dashboard web para control remoto.

---

## ✨ Funcionalidades

- **Reproducción** — Música desde YouTube y SoundCloud
- **Cola** — Sistema de cola con añadir, saltar, reordenar
- **Letras** — Búsqueda y visualización de letras en tiempo real
- **Ecualizador** — Ajuste de graves, agudos y volumen
- **Dashboard web** — Control remoto vía Flask (pausar, saltar, ver cola)

---

## 🛠 Stack

| Componente | Tecnología |
|------------|-----------|
| Bot Discord | discord.py |
| Audio | yt-dlp (YouTube/SoundCloud) |
| Dashboard | Flask |
| DB | SQLite |

---

## 🚀 Inicio rápido

```bash
git clone https://github.com/Noull999/MUUUSIK.git
cd MUUUSIK
pip install -r requirements.txt
# Crear .env con DISCORD_TOKEN
python main.py
```

---

## 📁 Estructura

```
MUUUSIK/
├── main.py          # Entry point del bot
├── cogs/
│   ├── music.py     # Comandos de música
│   └── __init__.py
├── keep_alive.py    # Health check / uptime
└── requirements.txt
```
