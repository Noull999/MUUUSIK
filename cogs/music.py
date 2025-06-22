import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
from collections import deque

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
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.current_song = {}
    
    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]
    
    async def play_next(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        if queue:
            next_song = queue.popleft()
            ctx.voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            self.current_song[ctx.guild.id] = next_song
            await ctx.send(f"🎵 Ahora reproduciendo: **{next_song.title}**")
    
    @commands.command(name='join', aliases=['connect'])
    async def join(self, ctx):
        """Conecta el bot a tu canal de voz"""
        if not ctx.author.voice:
            return await ctx.send("⚠️ Debes estar en un canal de voz!")
        
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        
        await ctx.send(f"✅ Conectado a {channel.name}")
    
    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, url):
        """Reproduce música desde YouTube o añade a la cola"""
        if not ctx.author.voice:
            return await ctx.send("⚠️ Debes estar en un canal de voz!")
        
        voice_client = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
                
                if not voice_client.is_playing():
                    voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
                    self.current_song[ctx.guild.id] = player
                    await ctx.send(f"🎵 Reproduciendo: **{player.title}**")
                else:
                    self.get_queue(ctx.guild.id).append(player)
                    await ctx.send(f"🎵 Añadido a la cola: **{player.title}**")
                    
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
                print(f"Error: {e}")
    
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
            await ctx.send("⏹ Reproducción detenida y cola limpiada")
    
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
        
        if ctx.voice_client.is_playing() or queue:
            current = self.current_song.get(ctx.guild.id)
            message = []
            
            if current:
                message.append(f"**Ahora sonando:** {current.title}\n")
            
            if queue:
                message.append("**Cola de reproducción:**")
                for i, song in enumerate(queue, 1):
                    message.append(f"{i}. {song.title}")
                
                await ctx.send("\n".join(message))
            else:
                await ctx.send("".join(message) + "\nNo hay más canciones en la cola")
        else:
            await ctx.send("⚠️ No hay canciones en la cola")
    
    @commands.command(name='volume', aliases=['vol'])
    async def volume(self, ctx, volume: int):
        """Ajusta el volumen (0-100)"""
        if ctx.voice_client is None:
            return await ctx.send("⚠️ No estoy conectado a un canal de voz")
        
        if 0 <= volume <= 100:
            ctx.voice_client.source.volume = volume / 100
            await ctx.send(f"🔊 Volumen ajustado a {volume}%")
        else:
            await ctx.send("⚠️ El volumen debe estar entre 0 y 100")
    
    @commands.command(name='leave', aliases=['disconnect'])
    async def leave(self, ctx):
        """Desconecta el bot del canal de voz"""
        if ctx.voice_client:
            self.get_queue(ctx.guild.id).clear()
            await ctx.voice_client.disconnect()
            await ctx.send("✅ Desconectado del canal de voz")
        else:
            await ctx.send("⚠️ No estoy conectado a un canal de voz")

async def setup(bot):
    await bot.add_cog(Music(bot))