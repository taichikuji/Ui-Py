from asyncio import get_running_loop, run_coroutine_threadsafe
from gc import collect
from random import shuffle
from typing import TYPE_CHECKING

from discord import (Embed, FFmpegPCMAudio, Interaction, Member, TextChannel,
                     VoiceChannel, VoiceClient, app_commands, VoiceState)
from discord.ext import commands
from yt_dlp import YoutubeDL

if TYPE_CHECKING:
    from main import UiPy


class MusicCog(commands.Cog):
    """Cog for music playback and queue management in voice channels."""
    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.voice_clients: dict[int, VoiceClient] = {}
        self.queues: dict[int, list[tuple[str, str, str]]] = {}
        self.currently_playing: dict[int, tuple[str, str, str]] = {}
        self.command_channels: dict[int, TextChannel] = {}
        self.ydl_opts = {
            "format": "bestaudio/best",
            "default_search": "ytsearch",
            "noplaylist": True,
            "quiet": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "no_warnings": True,
            "source_address": "0.0.0.0",
            "extract_flat": False,
        }
        self.ffmpeg_opts = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -analyzeduration 10M -probesize 10M",
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

        await interaction.response.defer()
        
        voice_channel = user.voice.channel
        vc: VoiceClient
        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            try:
                vc = await voice_channel.connect(self_deaf=True)
                self.voice_clients[guild_id] = vc
            except Exception as e:
                await interaction.followup.send(f":x: Failed to connect to the voice channel. Error: {e}", ephemeral=True)
                return
        else:
            vc = self.voice_clients[guild_id]
            if vc.channel and vc.channel != user.voice.channel:
                await interaction.followup.send(":x: I am already playing music in another voice channel.", ephemeral=True)
                return

        try:
            if info := await get_running_loop().run_in_executor(
                None, self._search_source, query
            ):
                if "entries" in info:
                    info = info["entries"][0]
                if "url" not in info:
                    raise ValueError("No URL found in the extracted information.")
                url = info["url"]
                title = info.get("title", "Unknown Title")
                duration = info.get("duration_string", "N/A")
            else:
                raise ValueError("Failed to extract information")
        except Exception as e:
            await interaction.followup.send(f":x: Failed to retrieve video. Error: {e}", ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            await interaction.followup.send(":x: This command must be used in a text channel.", ephemeral=True)
            return

        self.command_channels[guild_id] = channel

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        if not vc.is_playing() and not vc.is_paused() and not self.queues[guild_id]:
            self._play_song(guild_id, url, title, duration)
            await interaction.followup.send(f":notes: Now playing: **{title}** [{duration}]")
        else:
            self.queues[guild_id].append((url, title, duration))
            await interaction.followup.send(f":ballot_box_with_check: Added to queue: **{title}** [{duration}]")

    def _search_source(self, query: str):
        with YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)

    def _play_song(self, guild_id: int, url: str, title: str, duration: str):
        self.currently_playing[guild_id] = (url, title, duration)
        vc: VoiceClient = self.voice_clients[guild_id]
        vc.play(
            FFmpegPCMAudio(url, before_options=self.ffmpeg_opts["before_options"], options=self.ffmpeg_opts["options"]),
            after=lambda e: self._play_next(guild_id, e),
        )

    async def _disconnect_and_cleanup(self, guild_id: int):
        vc: VoiceClient | None = self.voice_clients.pop(guild_id, None)
        if vc:
            if vc.is_connected():
                try:
                    vc.stop()
                    await vc.disconnect()
                except Exception as e:
                    print(f"[ERROR] MusicCog: Error during disconnect for guild {guild_id}: {e}")
        try:
            self.queues.pop(guild_id, None)
            self.command_channels.pop(guild_id, None)
            self.currently_playing.pop(guild_id, None)
            collect()
        except Exception as e:
            print(f"[ERROR] MusicCog: Error during cleanup for guild {guild_id}: {e}")
        finally:
            return True

    def _play_next(self, guild_id: int, error=None):
        if error:
            print(f"[ERROR] MusicCog: Player error for guild {guild_id}: {error}")

        if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
            return
        
        if guild_id in self.queues and self.queues[guild_id]:
            url, title, duration = self.queues[guild_id].pop(0)
            self._play_song(guild_id, url, title, duration)
            if guild_id in self.command_channels and (channel := self.command_channels[guild_id]):
                coro = channel.send(f":notes: Now playing: **{title}** [{duration}]")
                future = run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    future.result(timeout=5)
                except Exception as e:
                    print(f"[ERROR] MusicCog: Error sending 'Now playing' message: {e}")
        else:
            self.currently_playing.pop(guild_id, None)
            self.bot.loop.create_task(self._disconnect_and_cleanup(guild_id))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot:
            return

        guild_id = member.guild.id
        if guild_id not in self.voice_clients:
            return

        vc = self.voice_clients[guild_id]
        if not vc.is_connected() or not vc.channel:
            return

        if before.channel == vc.channel and after.channel != vc.channel:
            if len(vc.channel.members) == 1 and vc.channel.members[0] == self.bot.user:
                await self._disconnect_and_cleanup(guild_id)

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

        queue_items = []
        if guild_id in self.currently_playing:
            _, title, duration = self.currently_playing[guild_id]
            queue_items.append(f"**Now Playing:** {title} [{duration}]")

        if guild_id in self.queues and self.queues[guild_id]:
            for i, (_, title, duration) in enumerate(self.queues[guild_id][:10]):
                queue_items.append(f"{i+1}. {title} [{duration}]")
            
            if len(self.queues[guild_id]) > 10:
                queue_items.append(f"\n...and {len(self.queues[guild_id]) - 10} more.")

        if not queue_items:
            await interaction.response.send_message(":x: The music queue is currently empty.")
        else:
            queue_list = "\n".join(queue_items)
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

    @app_commands.command(
        name="shuffle",
        description="Shuffle the current music queue."
    )
    async def shuffle(self, interaction: Interaction):
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id in self.queues and self.queues[guild_id]:
            shuffle(self.queues[guild_id])
            await interaction.response.send_message(":twisted_rightwards_arrows: Queue shuffled.")
        else:
            await interaction.response.send_message(":x: The music queue is currently empty.", ephemeral=True)

async def setup(bot: "UiPy"):
    await bot.add_cog(MusicCog(bot))
