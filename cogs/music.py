import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
from collections import deque
import subprocess

# Verificar FFmpeg
try:
    subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("✅ FFmpeg está instalado correctamente")
except Exception as e:
    print(f"❌ Error con FFmpeg: {e}")
    print("Instala FFmpeg y añádelo al PATH: https://ffmpeg.org/download.html")

# Configuración optimizada
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 20M -analyzeduration 20M',
    'options': '-vn -filter:a "volume=0.8"'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.8):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            
            if 'entries' in data:
                data = data['entries'][0]
                
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            print(f"Error al procesar URL: {e}")
            raise

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.current_song = {}
        self.loop = {}
        self.skip_votes = {}
        self.play_lock = asyncio.Lock()
        
    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]
    
    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("⚠️ Debes estar en un canal de voz primero!")
            return False
        
        permissions = ctx.author.voice.channel.permissions_for(ctx.me)
        if not permissions.connect or not permissions.speak:
            await ctx.send("⚠️ Necesito permisos para CONECTARME y HABLAR en este canal!")
            return False
        
        return True
    
    async def send_now_playing(self, ctx, song, is_loop=False):
        embed = discord.Embed(
            title="🎵 Reproduciendo ahora" + (" (LOOP)" if is_loop else ""),
            description=f"[{song.title}]({song.url})",
            color=discord.Color.blurple()
        )
        
        if hasattr(song, 'uploader') and song.uploader:
            embed.set_author(name=song.uploader)
            
        if hasattr(song, 'duration') and song.duration:
            try:
                total_seconds = int(float(song.duration))
                minutes, seconds = divmod(total_seconds, 60)
                hours, minutes = divmod(minutes, 60)
                
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
                    
                embed.add_field(name="Duración", value=duration_str)
            except (TypeError, ValueError):
                pass
                
        if hasattr(song, 'thumbnail') and song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
            
        await ctx.send(embed=embed)
    
    async def play_next(self, ctx):
        async with self.play_lock:
            if ctx.voice_client is None:
                return
                
            if self.loop.get(ctx.guild.id, False) and self.current_song.get(ctx.guild.id):
                song = self.current_song[ctx.guild.id]
                ctx.voice_client.play(
                    song, 
                    after=lambda e: self.bot.loop.create_task(self.play_next(ctx))
                )
                await self.send_now_playing(ctx, song, is_loop=True)
            else:
                queue = self.get_queue(ctx.guild.id)
                if queue:
                    next_song = queue.popleft()
                    ctx.voice_client.play(
                        next_song,
                        after=lambda e: self.bot.loop.create_task(self.play_next(ctx))
                    )
                    self.current_song[ctx.guild.id] = next_song
                    await self.send_now_playing(ctx, next_song)

    @commands.command(name='join', aliases=['connect'])
    async def join(self, ctx):
        """Conecta el bot a tu canal de voz"""
        if not await self.ensure_voice(ctx):
            return
        
        try:
            channel = ctx.author.voice.channel
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
            
            await ctx.send(f"✅ Conectado a {channel.name}")
        except Exception as e:
            await ctx.send(f"❌ Error al conectar: {str(e)}")

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, query):
        """Reproduce música desde YouTube o añade a la cola"""
        if not await self.ensure_voice(ctx):
            return
        
        voice_client = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        async with ctx.typing():
            try:
                query = query.strip('"\'')
                
                if not query.startswith(('http://', 'https://')):
                    query = f"ytsearch:{query}"
                
                player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
                
                if not voice_client.is_playing() and not voice_client.is_paused():
                    voice_client.play(
                        player, 
                        after=lambda e: self.bot.loop.create_task(self.play_next(ctx))
                    )
                    self.current_song[ctx.guild.id] = player
                    await self.send_now_playing(ctx, player)
                else:
                    self.get_queue(ctx.guild.id).append(player)
                    embed = discord.Embed(
                        description=f"🎵 Añadido a la cola: [{player.title}]({player.url})",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                    
            except youtube_dl.DownloadError as e:
                await ctx.send("❌ Error al descargar el audio. Intenta con otro enlace.")
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
                print(f"Error en play: {type(e)}: {e}")

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pausa la reproducción actual"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸ Reproducción pausada")
        else:
            await ctx.send("⚠️ No hay nada reproduciéndose")

    @commands.command(name='resume', aliases=['continue'])
    async def resume(self, ctx):
        """Reanuda la reproducción pausada"""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶ Reproducción reanudada")
        else:
            await ctx.send("⚠️ La reproducción no está pausada")

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Detiene la reproducción y limpia la cola"""
        if ctx.voice_client:
            ctx.voice_client.stop()
            self.get_queue(ctx.guild.id).clear()
            self.loop[ctx.guild.id] = False
            await ctx.send("⏹ Reproducción detenida y cola limpiada")
        else:
            await ctx.send("⚠️ No estoy conectado a un canal de voz")

    @commands.command(name='skip', aliases=['next'])
    async def skip(self, ctx):
        """Salta la canción actual"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭ Canción saltada")
            await self.play_next(ctx)
        else:
            await ctx.send("⚠️ No hay nada reproduciéndose")

    @commands.command(name='queue', aliases=['q'])
    async def queue(self, ctx):
        """Muestra la cola de reproducción actual"""
        queue = self.get_queue(ctx.guild.id)
        
        if not ctx.voice_client or (not ctx.voice_client.is_playing() and not queue):
            return await ctx.send("⚠️ No hay canciones en la cola")
        
        embed = discord.Embed(title="🎶 Cola de Reproducción", color=discord.Color.gold())
        
        if ctx.voice_client.is_playing() and self.current_song.get(ctx.guild.id):
            current = self.current_song[ctx.guild.id]
            embed.add_field(
                name="Ahora sonando",
                value=f"[{current.title}]({current.url})",
                inline=False
            )
        
        if queue:
            queue_list = []
            for i, song in enumerate(queue[:10], 1):
                queue_list.append(f"{i}. [{song.title}]({song.url})")
            
            embed.add_field(
                name=f"Próximas canciones ({len(queue)} total)",
                value="\n".join(queue_list) if queue_list else "No hay más canciones en la cola",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='nowplaying', aliases=['np'])
    async def nowplaying(self, ctx):
        """Muestra información de la canción actual"""
        if not ctx.voice_client or not ctx.voice_client.is_playing() or not self.current_song.get(ctx.guild.id):
            return await ctx.send("⚠️ No hay nada reproduciéndose")
        
        song = self.current_song[ctx.guild.id]
        await self.send_now_playing(ctx, song)

    @commands.command(name='loop')
    async def loop(self, ctx):
        """Activa/desactiva el loop de la canción actual"""
        guild_id = ctx.guild.id
        self.loop[guild_id] = not self.loop.get(guild_id, False)
        status = "🔂 Activado" if self.loop[guild_id] else "🔁 Desactivado"
        await ctx.send(f"{status} el loop para la canción actual")

    @commands.command(name='volume', aliases=['vol'])
    async def volume(self, ctx, volume: int):
        """Ajusta el volumen (0-100)"""
        if ctx.voice_client is None:
            return await ctx.send("⚠️ No estoy conectado a un canal de voz")
        
        if not 0 <= volume <= 100:
            return await ctx.send("⚠️ El volumen debe estar entre 0 y 100")
        
        if ctx.voice_client.source:
            ctx.voice_client.source.volume = volume / 100
            await ctx.send(f"🔊 Volumen ajustado a {volume}%")
        else:
            await ctx.send("⚠️ No hay nada reproduciéndose")

    @commands.command(name='leave', aliases=['disconnect'])
    async def leave(self, ctx):
        """Desconecta el bot del canal de voz"""
        if ctx.voice_client:
            self.get_queue(ctx.guild.id).clear()
            self.loop[ctx.guild.id] = False
            if ctx.guild.id in self.skip_votes:
                del self.skip_votes[ctx.guild.id]
            await ctx.voice_client.disconnect()
            await ctx.send("✅ Desconectado del canal de voz")
        else:
            await ctx.send("⚠️ No estoy conectado a un canal de voz")

    @commands.command(name='debug')
    async def debug(self, ctx):
        """Muestra información de depuración"""
        if not ctx.voice_client:
            return await ctx.send("No conectado a un canal de voz")
            
        embed = discord.Embed(title="🔧 Información de Depuración", color=discord.Color.orange())
        
        embed.add_field(name="Conectado en", value=ctx.voice_client.channel.name, inline=True)
        embed.add_field(name="Reproduciendo", value=ctx.voice_client.is_playing(), inline=True)
        embed.add_field(name="En pausa", value=ctx.voice_client.is_paused(), inline=True)
        
        if self.current_song.get(ctx.guild.id):
            song = self.current_song[ctx.guild.id]
            embed.add_field(name="Canción actual", value=song.title, inline=False)
            
        queue = self.get_queue(ctx.guild.id)
        embed.add_field(name="Tamaño de cola", value=len(queue), inline=True)
        embed.add_field(name="Loop activado", value=self.loop.get(ctx.guild.id, False), inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))