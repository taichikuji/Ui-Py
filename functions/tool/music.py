import logging
from os import environ
from random import shuffle as shuffle_list
from typing import TYPE_CHECKING

import wavelink
from discord import Embed, Interaction, Member, app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from main import UiPy

logger = logging.getLogger(__name__)

LAVALINK_URI = environ.get("LAVALINK_URI", "http://localhost:2333")
LAVALINK_PASSWORD = environ.get("LAVALINK_PASSWORD", "youshallnotpass")


class MusicCog(commands.Cog):
    """Cog for music playback and queue management via Lavalink."""

    def __init__(self, bot: "UiPy"):
        self.bot = bot

    async def cog_load(self):
        nodes = [wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASSWORD)]
        await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        logger.info("Lavalink node %s is ready.", payload.node.identifier)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player or not hasattr(player, "command_channel"):
            return

        track: wavelink.Playable = payload.track
        duration = self._format_duration(track.length)
        await player.command_channel.send(f":notes: Now playing: **{track.title}** [{duration}]")

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        if hasattr(player, "command_channel"):
            await player.command_channel.send(
                f":zzz: Inactive for `{player.inactive_timeout}` seconds. Disconnecting."
            )
        await player.disconnect()

    @app_commands.command(
        name="play",
        description="Play a song from YouTube. Provide a search term or URL.",
    )
    async def play(self, interaction: Interaction, query: str):
        if not query:
            await interaction.response.send_message(
                ":x: You must provide a search term or URL.", ephemeral=True
            )
            return

        user = interaction.user
        if not isinstance(user, Member):
            await interaction.response.send_message(
                ":x: This command can only be used in a server.", ephemeral=True
            )
            return

        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(
                ":x: You need to be in a voice channel to use this command.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        player: wavelink.Player = (
            interaction.guild.voice_client
            or await user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        )

        if player.channel != user.voice.channel:
            await interaction.followup.send(
                ":x: I am already playing music in another voice channel.",
                ephemeral=True,
            )
            return

        player.inactive_timeout = 120
        player.command_channel = interaction.channel

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
            if not tracks:
                await interaction.followup.send(
                    ":x: No results found for your query.", ephemeral=True
                )
                return

            if isinstance(tracks, wavelink.Playlist):
                added: int = await player.queue.put_wait(tracks)
                await interaction.followup.send(
                    f":ballot_box_with_check: Added playlist **{tracks.name}** ({added} songs) to the queue."
                )
            else:
                track: wavelink.Playable = tracks[0]
                await player.queue.put_wait(track)
                duration = self._format_duration(track.length)
                if player.playing:
                    await interaction.followup.send(
                        f":ballot_box_with_check: Added to queue: **{track.title}** [{duration}]"
                    )
                else:
                    await interaction.followup.send(
                        f":notes: Now playing: **{track.title}** [{duration}]"
                    )

            if not player.playing:
                await player.play(player.queue.get())

        except Exception as e:
            logger.error("Failed to play query '%s': %s", query, e)
            await interaction.followup.send(
                f":x: Failed to retrieve track. Error: {e}", ephemeral=True
            )

    @app_commands.command(
        name="stop",
        description="Stop the currently playing music and disconnect.",
    )
    async def stop(self, interaction: Interaction):
        player: wavelink.Player | None = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                ":x: The bot is not connected to a voice channel.", ephemeral=True
            )
            return

        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message(":stop_button: Stopped and disconnected.")

    @app_commands.command(
        name="pause",
        description="Pause the currently playing music.",
    )
    async def pause(self, interaction: Interaction):
        player: wavelink.Player | None = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                ":x: The bot is not connected to a voice channel.", ephemeral=True
            )
            return

        if not player.playing:
            await interaction.response.send_message(
                ":x: No music is currently playing.", ephemeral=True
            )
            return

        if player.paused:
            await interaction.response.send_message(
                ":x: The music is already paused.", ephemeral=True
            )
            return

        await player.pause(True)
        await interaction.response.send_message(":pause_button: Music paused.")

    @app_commands.command(
        name="resume",
        description="Resume the paused music.",
    )
    async def resume(self, interaction: Interaction):
        player: wavelink.Player | None = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                ":x: The bot is not connected to a voice channel.", ephemeral=True
            )
            return

        if not player.paused:
            await interaction.response.send_message(
                ":x: The music is not paused.", ephemeral=True
            )
            return

        await player.pause(False)
        await interaction.response.send_message(":arrow_forward: Music resumed.")

    @app_commands.command(
        name="skip",
        description="Skip the current song.",
    )
    async def skip(self, interaction: Interaction):
        player: wavelink.Player | None = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                ":x: The bot is not connected to a voice channel.", ephemeral=True
            )
            return

        if not player.playing:
            await interaction.response.send_message(
                ":x: No music is currently playing.", ephemeral=True
            )
            return

        await player.skip()
        await interaction.response.send_message(":track_next: Skipped.")

    @app_commands.command(
        name="queue",
        description="Show the current music queue. Displays up to 10 items and indicates if there are more.",
    )
    async def queue(self, interaction: Interaction):
        player: wavelink.Player | None = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                ":x: The music queue is currently empty."
            )
            return

        queue_items = []
        if player.current:
            duration = self._format_duration(player.current.length)
            queue_items.append(f"**Now Playing:** {player.current.title} [{duration}]")

        if not player.queue.is_empty:
            for i, track in enumerate(list(player.queue)[:10]):
                duration = self._format_duration(track.length)
                queue_items.append(f"{i + 1}. {track.title} [{duration}]")

            if player.queue.count > 10:
                queue_items.append(f"\n...and {player.queue.count - 10} more.")

        if not queue_items:
            await interaction.response.send_message(
                ":x: The music queue is currently empty."
            )
        else:
            embed = Embed(
                title=":notes: Music Queue",
                description="\n".join(queue_items),
                color=self.bot.color,
            )
            await interaction.response.send_message(embed=embed)

    # NOTE: /nowplaying command is intentionally omitted.
    # By design, a message is already sent to the channel when a song starts playing.

    @app_commands.command(
        name="shuffle",
        description="Shuffle the current music queue.",
    )
    async def shuffle(self, interaction: Interaction):
        player: wavelink.Player | None = interaction.guild.voice_client
        if not player or player.queue.is_empty:
            await interaction.response.send_message(
                ":x: The music queue is currently empty.", ephemeral=True
            )
            return

        tracks = list(player.queue)
        player.queue.clear()
        shuffle_list(tracks)
        for track in tracks:
            await player.queue.put_wait(track)

        await interaction.response.send_message(
            ":twisted_rightwards_arrows: Queue shuffled."
        )

    @staticmethod
    def _format_duration(ms: int) -> str:
        seconds = ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


async def setup(bot: "UiPy"):
    await bot.add_cog(MusicCog(bot))
