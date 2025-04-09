from discord.ext import commands
from discord import FFmpegPCMAudio
from yt_dlp import YoutubeDL
from typing import TYPE_CHECKING
from asyncio import get_running_loop

if TYPE_CHECKING:
    from main import UiPyBot

class MusicCog(commands.Cog):
    def __init__(self, bot: 'UiPyBot'):
        self.bot = bot
        self.voice_clients = {}
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch',
            'noplaylist': True,
            'quiet': True,
            'extract_flat': False,
        }
        self.ffmpeg_opts = {
            'options': '-vn',
        }

    @commands.hybrid_command(
        name="play",
        description="Play a song from YouTube. Provide a search term or URL."
    )
    async def play(self, ctx: commands.Context, *, query: str = None):
        if not query:
            description = ":x: You must provide a search term or URL."
            if ctx.interaction:
                await ctx.interaction.response.send_message(description, ephemeral=True)
            else:
                await ctx.send(description)
            return

        if not ctx.author.voice:
            description = ":x: You need to be in a voice channel to use this command."
            if ctx.interaction:
                await ctx.interaction.response.send_message(description, ephemeral=True)
            else:
                await ctx.send(description)
            return

        voice_channel = ctx.author.voice.channel

        if ctx.guild.id not in self.voice_clients or not self.voice_clients[ctx.guild.id].is_connected():
            vc = await voice_channel.connect()
            self.voice_clients[ctx.guild.id] = vc
        else:
            vc = self.voice_clients[ctx.guild.id]

        if ctx.interaction:
            await ctx.interaction.response.defer()

        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = await get_running_loop().run_in_executor(None , lambda: ydl.extract_info(query, download=False))
                if 'entries' in info:
                    info = info['entries'][0]
                if 'url' not in info:
                    raise ValueError("No URL found in the extracted information.")
                url = info['url']
                title = info.get('title', 'Unknown Title')
            except Exception as e:
                description = f":x: Failed to retrieve video. Error: {e}"
                if ctx.interaction:
                    await ctx.interaction.followup.send(description, ephemeral=True)
                else:
                    await ctx.send(description)
                return

        vc.stop()
        vc.play(FFmpegPCMAudio(url, **self.ffmpeg_opts))
        description = f":notes: Now playing: **{title}**"
        if ctx.interaction:
            await ctx.interaction.followup.send(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(
        name="stop",
        description="Stop the currently playing music and disconnect."
    )
    async def stop(self, ctx: commands.Context):
        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            description = ":stop_button: Stopped and disconnected."
        else:
            description = ":x: The bot is not connected to a voice channel."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(
        name="pause",
        description="Pause the currently playing music."
    )
    async def pause(self, ctx: commands.Context):
        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            if vc.is_playing():
                vc.pause()
                description = ":pause_button: Music paused."
            else:
                description = ":x: No music is currently playing."
        else:
            description = ":x: The bot is not connected to a voice channel."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(
        name="resume",
        description="Resume the paused music."
    )
    async def resume(self, ctx: commands.Context):
        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            if vc.is_paused():
                vc.resume()
                description = ":arrow_forward: Music resumed."
            else:
                description = ":x: The music is not paused."
        else:
            description = ":x: The bot is not connected to a voice channel."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

async def setup(bot: 'UiPyBot'):
    await bot.add_cog(MusicCog(bot))
