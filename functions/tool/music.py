from discord.ext import commands
from discord import FFmpegPCMAudio
from yt_dlp import YoutubeDL
from typing import TYPE_CHECKING, Dict, List, Tuple
from asyncio import get_running_loop, run_coroutine_threadsafe

if TYPE_CHECKING:
    from main import UiPy


class MusicCog(commands.Cog):
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.voice_clients = {}
        self.queues: Dict[int, List[Tuple[str, str]]] = {}
        self.command_channels = {}
        self.ydl_opts = {
            "format": "bestaudio/best",
            "default_search": "ytsearch",
            "noplaylist": True,
            "quiet": True,
            "extract_flat": False,
        }
        self.ffmpeg_opts = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

    @commands.hybrid_command(
        name="play",
        description="Play a song from YouTube. Provide a search term or URL.",
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

        if (
            ctx.guild.id not in self.voice_clients
            or not self.voice_clients[ctx.guild.id].is_connected()
        ):
            vc = await voice_channel.connect()
            self.voice_clients[ctx.guild.id] = vc
        else:
            vc = self.voice_clients[ctx.guild.id]

        if ctx.interaction:
            await ctx.interaction.response.defer()

        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = await get_running_loop().run_in_executor(
                    None, lambda: ydl.extract_info(query, download=False)
                )
                if "entries" in info:
                    info = info["entries"][0]
                if "url" not in info:
                    raise ValueError("No URL found in the extracted information.")
                url = info["url"]
                title = info.get("title", "Unknown Title")
            except Exception as e:
                description = f":x: Failed to retrieve video. Error: {e}"
                if ctx.interaction:
                    await ctx.interaction.followup.send(description, ephemeral=True)
                else:
                    await ctx.send(description)
                return

        self.command_channels[ctx.guild.id] = ctx.channel

        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []

        if not vc.is_playing() and not vc.is_paused() and not self.queues[ctx.guild.id]:
            self._play_song(ctx.guild.id, url, title)
            description = f":notes: Now playing: **{title}**"
        else:
            self.queues[ctx.guild.id].append((url, title))
            description = f":ballot_box_with_check: Added to queue: **{title}**"

        if ctx.interaction:
            await ctx.interaction.followup.send(description, ephemeral=True)
        else:
            await ctx.send(description)

    def _play_song(self, guild_id: int, url: str, title: str):
        vc = self.voice_clients[guild_id]
        vc.play(
            FFmpegPCMAudio(url, **self.ffmpeg_opts),
            after=lambda e: self._play_next(guild_id, e),
        )

    async def _disconnect_and_cleanup(self, guild_id: int):
        if guild_id in self.voice_clients:
            vc = self.voice_clients[guild_id]
            if vc.is_connected():
                await vc.disconnect()
                
            del self.voice_clients[guild_id]
            if guild_id in self.queues:
                self.queues[guild_id].clear()
        
        return True
    def _play_next(self, guild_id: int, error=None):
        if error:
            print(f"Player error: {error}")

        if guild_id in self.queues and self.queues[guild_id]:
            url, title = self.queues[guild_id].pop(0)
            self._play_song(guild_id, url, title)
            if guild_id in self.command_channels and self.command_channels[guild_id]:
                channel = self.command_channels[guild_id]
                coro = channel.send(f":notes: Now playing: **{title}**")
                future = run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    future.result()
                except:
                    pass
        else:
            coro = self._disconnect_and_cleanup(guild_id)
            future = run_coroutine_threadsafe(coro, self.bot.loop)

    @commands.hybrid_command(
        name="stop", description="Stop the currently playing music and disconnect."
    )
    async def stop(self, ctx: commands.Context):
        if ctx.guild.id in self.voice_clients:
            await self._disconnect_and_cleanup(ctx.guild.id)
            description = ":stop_button: Stopped and disconnected."
        else:
            description = ":x: The bot is not connected to a voice channel."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(
        name="pause", description="Pause the currently playing music."
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

    @commands.hybrid_command(name="resume", description="Resume the paused music.")
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

    @commands.hybrid_command(name="queue", description="Show the current music queue.")
    async def queue(self, ctx: commands.Context):
        if ctx.guild.id not in self.queues or not self.queues[ctx.guild.id]:
            description = ":x: The queue is empty."
        else:
            queue_list = "\n".join(
                [
                    f"{i+1}. {title}"
                    for i, (_, title) in enumerate(self.queues[ctx.guild.id])
                ]
            )
            description = f":musical_note: **Current Queue:**\n{queue_list}"

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)

    @commands.hybrid_command(name="skip", description="Skip the current song.")
    async def skip(self, ctx: commands.Context):
        if ctx.guild.id in self.voice_clients:
            vc = self.voice_clients[ctx.guild.id]
            if vc.is_playing() or vc.is_paused():
                vc.stop()
                description = ":track_next: Skipped."
            else:
                description = ":x: No music is currently playing."
        else:
            description = ":x: The bot is not connected to a voice channel."

        if ctx.interaction:
            await ctx.interaction.response.send_message(description, ephemeral=True)
        else:
            await ctx.send(description)


async def setup(bot: "UiPy"):
    await bot.add_cog(MusicCog(bot))
