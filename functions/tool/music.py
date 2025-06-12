from typing import TYPE_CHECKING, Dict, List, Tuple
from asyncio import get_running_loop, run_coroutine_threadsafe
from discord.ext import commands
from discord import FFmpegPCMAudio, Interaction, app_commands, VoiceClient, TextChannel, Member, Embed
from yt_dlp import YoutubeDL

if TYPE_CHECKING:
    from main import UiPy


class MusicCog(commands.Cog):
    """Cog for music playback and queue management in voice channels."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.voice_clients: Dict[int, VoiceClient] = {}
        self.queues: Dict[int, List[Tuple[str, str]]] = {}
        self.command_channels: Dict[int, TextChannel] = {}
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

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return

        user = interaction.user
        if not isinstance(user, Member):
            await interaction.response.send_message(":x: This command can only be used in a server.", ephemeral=True)
            return

        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(":x: You need to be in a voice channel to use this command.", ephemeral=True)
            return

        voice_channel = user.voice.channel
        vc: VoiceClient
        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            vc = await voice_channel.connect()
            self.voice_clients[guild_id] = vc
        else:
            vc = self.voice_clients[guild_id]

        await interaction.response.defer()

        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                if info := await get_running_loop().run_in_executor(
                    None, lambda: ydl.extract_info(query, download=False)
                ):
                    if "entries" in info:
                        info = info["entries"][0]
                    if "url" not in info:
                        raise ValueError("No URL found in the extracted information.")
                    url = info["url"]
                    title = info.get("title", "Unknown Title")
                else:
                    raise ValueError("Failed to extract information")
            except Exception as e:
                await interaction.followup.send(f":x: Failed to retrieve video. Error: {e}", ephemeral=True)
                return

        channel = interaction.channel
        if not isinstance(channel, TextChannel):
            await interaction.followup.send(":x: This command must be used in a text channel.", ephemeral=True)
            return

        self.command_channels[guild_id] = channel

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        if not vc.is_playing() and not vc.is_paused() and not self.queues[guild_id]:
            self._play_song(guild_id, url)
            await interaction.followup.send(f":notes: Now playing: **{title}**")
        else:
            self.queues[guild_id].append((url, title))
            await interaction.followup.send(f":ballot_box_with_check: Added to queue: **{title}**")

    def _play_song(self, guild_id: int, url: str):
        vc: VoiceClient = self.voice_clients[guild_id]
        vc.play(
            FFmpegPCMAudio(url, before_options=self.ffmpeg_opts["before_options"], options=self.ffmpeg_opts["options"]),
            after=lambda e: self._play_next(guild_id, e),
        )

    async def _disconnect_and_cleanup(self, guild_id: int):
        if guild_id in self.voice_clients:
            vc: VoiceClient = self.voice_clients[guild_id]
            if vc.is_connected():
                await vc.disconnect()
                
            del self.voice_clients[guild_id]
            if guild_id in self.queues:
                self.queues[guild_id].clear()
        
        return True

    def _play_next(self, guild_id: int, error=None):
        if error:
            print(f"Player error for guild {guild_id}: {error}")

        if (guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected()):
            return
        
        if guild_id in self.queues and self.queues[guild_id]:
            url, title = self.queues[guild_id].pop(0)
            self._play_song(guild_id, url)
            if guild_id in self.command_channels and (channel := self.command_channels[guild_id]):
                coro = channel.send(f":notes: Now playing: **{title}**")
                future = run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    future.result()
                except Exception as e:
                    print(f"Error sending message: {e}")
        else:
            coro = self._disconnect_and_cleanup(guild_id)
            future = run_coroutine_threadsafe(coro, self.bot.loop)

    @app_commands.command(
        name="stop",
        description="Stop the currently playing music and disconnect."
    )
    async def stop(self, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id in self.voice_clients:
            await self._disconnect_and_cleanup(guild_id)
            await interaction.response.send_message(":stop_button: Stopped and disconnected.")
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)

    @app_commands.command(
        name="pause",
        description="Pause the currently playing music."
    )
    async def pause(self, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id in self.voice_clients:
            vc: VoiceClient = self.voice_clients[guild_id]
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
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id in self.voice_clients:
            vc: VoiceClient = self.voice_clients[guild_id]
            if vc.is_paused():
                vc.resume()
                await interaction.response.send_message(":arrow_forward: Music resumed.")
            else:
                await interaction.response.send_message(":x: The music is not paused.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)

    @app_commands.command(
        name="queue",
        description="Show the current music queue. Displays up to 10 items and indicates if there are more."
    )
    async def queue(self, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id not in self.queues or not self.queues[guild_id]:
            await interaction.response.send_message(":x: The music queue is currently empty.")
        else:
            queue_list = "\n".join(
                [
                    f"{i+1}. {title}"
                    for i, (_, title) in enumerate(self.queues[guild_id][:10])
                ]
            )
            if len(self.queues[guild_id]) > 10:
                queue_list += f"\n...and {len(self.queues[guild_id]) - 10} more."
            em = {
                "title": ":notes: Music Queue",
                "description": queue_list,
                "color": self.bot.color,
            }
            await interaction.response.send_message(embed=Embed.from_dict(em))

    @app_commands.command(
        name="skip",
        description="Skip the current song."
    )
    async def skip(self, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id in self.voice_clients:
            vc: VoiceClient = self.voice_clients[guild_id]
            if vc.is_playing() or vc.is_paused():
                vc.stop()
                await interaction.response.send_message(":track_next: Skipped.")
            else:
                await interaction.response.send_message(":x: No music is currently playing.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)


async def setup(bot: "UiPy"):
    await bot.add_cog(MusicCog(bot))
