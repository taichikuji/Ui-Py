from discord.ext import commands
from discord import FFmpegPCMAudio, Interaction, app_commands
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

    @app_commands.command(
        name="play",
        description="Play a song from YouTube. Provide a search term or URL.",
    )
    async def play(self, interaction: Interaction, query: str):
        if not query:
            await interaction.response.send_message(":x: You must provide a search term or URL.", ephemeral=True)
            return

        if not interaction.user.voice:
            await interaction.response.send_message(":x: You need to be in a voice channel to use this command.", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel

        if (
            interaction.guild_id not in self.voice_clients
            or not self.voice_clients[interaction.guild_id].is_connected()
        ):
            vc = await voice_channel.connect()
            self.voice_clients[interaction.guild_id] = vc
        else:
            vc = self.voice_clients[interaction.guild_id]

        await interaction.response.defer()

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
                await interaction.followup.send(f":x: Failed to retrieve video. Error: {e}", ephemeral=True)
                return

        self.command_channels[interaction.guild_id] = interaction.channel

        if interaction.guild_id not in self.queues:
            self.queues[interaction.guild_id] = []

        if not vc.is_playing() and not vc.is_paused() and not self.queues[interaction.guild_id]:
            self._play_song(interaction.guild_id, url, title)
            await interaction.followup.send(f":notes: Now playing: **{title}**")
        else:
            self.queues[interaction.guild_id].append((url, title))
            await interaction.followup.send(f":ballot_box_with_check: Added to queue: **{title}**")

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

    @app_commands.command(
        name="stop",
        description="Stop the currently playing music and disconnect."
    )
    async def stop(self, interaction: Interaction):
        if interaction.guild_id in self.voice_clients:
            await self._disconnect_and_cleanup(interaction.guild_id)
            await interaction.response.send_message(":stop_button: Stopped and disconnected.")
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)

    @app_commands.command(
        name="pause",
        description="Pause the currently playing music."
    )
    async def pause(self, interaction: Interaction):
        if interaction.guild_id in self.voice_clients:
            vc = self.voice_clients[interaction.guild_id]
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message(":pause_button: Music paused.")
            else:
                await interaction.response.send_message(":x: No music is currently playing.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)

    @app_commands.command(
        name="resume",
        description="Resume the paused music."
    )
    async def resume(self, interaction: Interaction):
        if interaction.guild_id in self.voice_clients:
            vc = self.voice_clients[interaction.guild_id]
            if vc.is_paused():
                vc.resume()
                await interaction.response.send_message(":arrow_forward: Music resumed.")
            else:
                await interaction.response.send_message(":x: The music is not paused.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)

    @app_commands.command(
        name="queue",
        description="Show the current music queue."
    )
    async def queue(self, interaction: Interaction):
        if interaction.guild_id not in self.queues or not self.queues[interaction.guild_id]:
            await interaction.response.send_message(":x: The queue is empty.")
        else:
            queue_list = "\n".join(
                [
                    f"{i+1}. {title}"
                    for i, (_, title) in enumerate(self.queues[interaction.guild_id])
                ]
            )
            await interaction.response.send_message(f":musical_note: **Current Queue:**\n{queue_list}")

    @app_commands.command(
        name="skip",
        description="Skip the current song."
    )
    async def skip(self, interaction: Interaction):
        if interaction.guild_id in self.voice_clients:
            vc = self.voice_clients[interaction.guild_id]
            if vc.is_playing() or vc.is_paused():
                vc.stop()
                await interaction.response.send_message(":track_next: Skipped.")
            else:
                await interaction.response.send_message(":x: No music is currently playing.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)

async def setup(bot: "UiPy"):
    await bot.add_cog(MusicCog(bot))
