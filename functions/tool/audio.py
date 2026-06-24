import logging
import re
from asyncio import get_running_loop, run_coroutine_threadsafe
from random import choice, shuffle
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

from discord import (Embed, FFmpegPCMAudio, Interaction, Member, TextChannel, Thread,
                     VoiceChannel, VoiceClient, VoiceState, app_commands)
from discord.ext import commands
from yt_dlp import YoutubeDL

if TYPE_CHECKING:
    from main import UiPy

logger = logging.getLogger(__name__)

RADIO_API_BASE = "https://radio.garden/api"
_CHANNEL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")
_LISTEN_URL_RE = re.compile(r"/listen/[^/]+/([A-Za-z0-9_-]+)", re.IGNORECASE)


class AudioCog(commands.Cog):
    """Cog for unified audio playback (music + radio)."""

    def __init__(self, bot: "UiPy"):
        self.bot = bot
        self.voice_clients: dict[int, VoiceClient] = {}
        self.queues: dict[int, list[tuple[str, str, str, str | None]]] = {}
        self.currently_playing: dict[int, tuple[str, str, str]] = {}
        self.command_channels: dict[int, TextChannel | VoiceChannel | Thread] = {}
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

    @app_commands.command(name="play", description="Play a song from YouTube. Provide a search term or URL.")
    async def play(self, interaction: Interaction, query: str):
        if not query:
            await interaction.response.send_message(":x: You must provide a search term or URL.", ephemeral=True)
            return
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if not isinstance(user := interaction.user, Member):
            await interaction.response.send_message(":x: This command can only be used in a server.", ephemeral=True)
            return
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(":x: You need to be in a voice channel to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        vc = await self._get_or_connect_voice_client(guild_id, user.voice.channel, interaction)
        if vc is None:
            return
        channel = self._resolve_command_channel(interaction)
        if channel is None:
            await interaction.followup.send(":x: This command must be used in a text channel.", ephemeral=True)
            return
        self.command_channels[guild_id] = channel

        try:
            info = await get_running_loop().run_in_executor(None, self._search_source, query)
            if not info:
                raise ValueError("Failed to extract information.")
            if "entries" in info:
                if not info["entries"]:
                    raise ValueError("No results found.")
                info = info["entries"][0]
            stream_url = info.get("url")
            if not (webpage_url := info.get("webpage_url")):
                raise ValueError("No webpage URL found.")
        except Exception as e:
            await interaction.followup.send(f":x: Failed to retrieve video. Error: {e}", ephemeral=True)
            return

        title = info.get("title", "Unknown Title")
        duration = info.get("duration_string", "N/A")
        await self._enqueue_or_play(
            guild_id,
            source_url=webpage_url,
            title=title,
            duration=duration,
            stream_url=stream_url,
            followup=interaction.followup.send,
        )

    @app_commands.command(
        name="radio",
        description="Play a radio station from a radio source. Random if no input.",
    )
    @app_commands.describe(
        input="A station query, radio URL, or channel ID.",
        region="Optional region/country hint for query disambiguation (e.g. Netherlands, Hoofddorp).",
    )
    async def radio(self, interaction: Interaction, input: str | None = None, region: str | None = None):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if not isinstance(user := interaction.user, Member):
            await interaction.response.send_message(":x: This command can only be used in a server.", ephemeral=True)
            return
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(":x: You need to be in a voice channel to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        channel = self._resolve_command_channel(interaction)
        if channel is None:
            await interaction.followup.send(":x: This command must be used in a text channel.", ephemeral=True)
            return

        try:
            channel_id, title = await self._resolve_radio_station(input, region)
        except ValueError as e:
            await interaction.followup.send(f":x: {e}", ephemeral=True)
            return
        except Exception as e:
            logger.error("radio station resolution failed: %s", e)
            await interaction.followup.send(":x: Failed to reach radio source. Try again later.", ephemeral=True)
            return

        stream_api_url = f"{RADIO_API_BASE}/ara/content/listen/{channel_id}/channel.mp3"
        try:
            stream_url = await self._extract_stream_url_with_ytdlp(stream_api_url)
        except ValueError:
            try:
                stream_url = await self._resolve_radio_stream_url(channel_id)
            except ValueError as e:
                await interaction.followup.send(f":x: {e}", ephemeral=True)
                return
            except Exception as e:
                logger.error("radio stream URL resolution failed: %s", e)
                await interaction.followup.send(":x: Failed to reach radio source. Try again later.", ephemeral=True)
                return
        except Exception as e:
            logger.error("radio stream URL extraction failed: %s", e)
            await interaction.followup.send(":x: Failed to reach radio source. Try again later.", ephemeral=True)
            return

        vc = await self._get_or_connect_voice_client(guild_id, user.voice.channel, interaction)
        if vc is None:
            return
        self.command_channels[guild_id] = channel

        await self._enqueue_or_play(
            guild_id,
            source_url=stream_api_url,
            title=title,
            duration="LIVE",
            stream_url=stream_url,
            followup=interaction.followup.send,
            now_playing_message=f":radio: Playing **{title}** on Radio Garden",
            queue_message=f":ballot_box_with_check: Added to queue: :radio: **{title}** [LIVE]",
        )

    async def _enqueue_or_play(
        self,
        guild_id: int,
        *,
        source_url: str,
        title: str,
        duration: str,
        stream_url: str | None,
        followup,
        now_playing_message: str | None = None,
        queue_message: str | None = None,
    ) -> None:
        vc = self.voice_clients.get(guild_id)
        if vc is None or not vc.is_connected():
            await followup(":x: The bot is not connected to a voice channel.", ephemeral=True)
            return

        self.queues.setdefault(guild_id, [])
        if vc.is_playing() or vc.is_paused() or self.queues[guild_id]:
            # For YouTube entries, stream URL can expire. Re-resolve on playback.
            queued_stream_url = stream_url if duration == "LIVE" else None
            self.queues[guild_id].append((source_url, title, duration, queued_stream_url))
            await followup(queue_message or f":ballot_box_with_check: Added to queue: **{title}** [{duration}]")
            return

        started = await self._play_song(guild_id, source_url, stream_url, title, duration)
        if started:
            await followup(now_playing_message or f":notes: Now playing: **{title}** [{duration}]")
        else:
            await followup(":x: Failed to start playback.", ephemeral=True)

    @staticmethod
    def _resolve_command_channel(interaction: Interaction) -> TextChannel | VoiceChannel | Thread | None:
        if isinstance(interaction.channel, (TextChannel, VoiceChannel, Thread)):
            return interaction.channel
        return None

    async def _get_or_connect_voice_client(
        self, guild_id: int, user_voice_channel: VoiceChannel, interaction: Interaction
    ) -> VoiceClient | None:
        vc = self.voice_clients.get(guild_id)
        if vc is None or not vc.is_connected():
            try:
                vc = await user_voice_channel.connect(self_deaf=True)
                self.voice_clients[guild_id] = vc
            except Exception as e:
                await interaction.followup.send(f":x: Failed to connect to the voice channel. Error: {e}", ephemeral=True)
                return None
        elif vc.channel and vc.channel != user_voice_channel:
            await interaction.followup.send(":x: I am already playing in another voice channel.", ephemeral=True)
            return None
        return vc

    def _search_source(self, query: str):
        with YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)

    async def _play_next_track_and_announce(
        self, guild_id: int, source_url: str, title: str, duration: str, stream_url: str | None
    ):
        started = await self._play_song(guild_id, source_url, stream_url, title, duration)
        if not started:
            return
        if guild_id in self.command_channels and (channel := self.command_channels[guild_id]):
            if duration == "LIVE":
                await channel.send(f":radio: Playing **{title}** on Radio Garden")
            else:
                await channel.send(f":notes: Now playing: **{title}** [{duration}]")

    async def _ensure_user_in_same_voice_channel(self, interaction: Interaction, guild_id: int) -> VoiceClient | None:
        if not isinstance(user := interaction.user, Member):
            await interaction.response.send_message(":x: This command can only be used in a server.", ephemeral=True)
            return None
        if not user.voice or not user.voice.channel:
            await interaction.response.send_message(":x: You need to be in a voice channel to use this command.", ephemeral=True)
            return None

        vc = self.voice_clients.get(guild_id)
        if vc is None or not vc.is_connected() or vc.channel is None:
            await interaction.response.send_message(":x: The bot is not connected to a voice channel.", ephemeral=True)
            return None
        if user.voice.channel != vc.channel:
            await interaction.response.send_message(
                ":x: You must be in the same voice channel as the bot to use this command.",
                ephemeral=True,
            )
            return None
        return vc

    async def _play_song(
        self,
        guild_id: int,
        source_url: str,
        stream_url: str | None,
        title: str,
        duration: str,
    ) -> bool:
        if not stream_url:
            try:
                info = await get_running_loop().run_in_executor(None, self._search_source, source_url)
                if "entries" in info:
                    if not info["entries"]:
                        raise ValueError("No results found while refreshing stream URL.")
                    info = info["entries"][0]
                stream_url = info.get("url")
            except Exception as e:
                logger.error("Could not refresh URL for %s: %s", title, e)
                self._play_next(guild_id)
                return False

        if not stream_url:
            logger.error("No playable stream URL found for %s", title)
            self._play_next(guild_id)
            return False

        vc = self.voice_clients.get(guild_id)
        if vc is None or not vc.is_connected():
            logger.warning("Voice client disappeared before playback in guild %s", guild_id)
            return False

        self.currently_playing[guild_id] = (source_url, title, duration)
        try:
            vc.play(
                FFmpegPCMAudio(
                    stream_url,
                    before_options=self.ffmpeg_opts["before_options"],
                    options=self.ffmpeg_opts["options"],
                ),
                after=lambda e: self._play_next(guild_id, e),
            )
            return True
        except Exception as e:
            logger.error("Playback failed to start in guild %s: %s", guild_id, e)
            self._play_next(guild_id, e)
            return False

    async def _disconnect_and_cleanup(self, guild_id: int):
        if (vc := self.voice_clients.pop(guild_id, None)) and vc.is_connected():
            try:
                vc.stop()
                await vc.disconnect()
            except Exception as e:
                logger.error("Error during disconnect for guild %s: %s", guild_id, e)
        self.queues.pop(guild_id, None)
        self.command_channels.pop(guild_id, None)
        self.currently_playing.pop(guild_id, None)

    def _play_next(self, guild_id: int, error=None):
        if error:
            logger.error("Player error for guild %s: %s", guild_id, error)
        vc = self.voice_clients.get(guild_id)
        if vc is None or not vc.is_connected():
            return

        queue = self.queues.get(guild_id)
        if queue:
            source_url, title, duration, stream_url = queue.pop(0)
            coro = self._play_next_track_and_announce(guild_id, source_url, title, duration, stream_url)
            run_coroutine_threadsafe(coro, self.bot.loop)
            return

        self.currently_playing.pop(guild_id, None)
        run_coroutine_threadsafe(self._disconnect_and_cleanup(guild_id), self.bot.loop)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot:
            return

        guild_id = member.guild.id
        vc = self.voice_clients.get(guild_id)
        if vc is None:
            return

        if not vc.is_connected() or not vc.channel:
            return

        if before.channel == vc.channel and after.channel != vc.channel:
            if len(vc.channel.members) == 1 and vc.channel.members[0] == self.bot.user:
                await self._disconnect_and_cleanup(guild_id)

    async def _resolve_radio_station(self, query: str | None, region: str | None = None) -> tuple[str, str]:
        if query is None or not query.strip():
            return await self._pick_random_station()

        raw = query.strip()
        if channel_id := self._extract_channel_id(raw):
            if channel := await self._fetch_radio_channel(channel_id):
                title = channel.get("title") or "Unknown Station"
                return channel_id, title

        channel = await self._search_radio_channel(raw, region)
        if channel is None:
            if region:
                raise ValueError(f"No radio station found for query '{raw}' in region '{region}'.")
            raise ValueError("No radio station found for that query.")

        if not (channel_id := self._channel_id_from_href(channel.get("url"))):
            raise ValueError("Could not resolve a station stream ID from search results.")
        title = channel.get("title") or "Unknown Station"
        return channel_id, title

    @staticmethod
    def _extract_channel_id(value: str) -> str | None:
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            if parsed.netloc.lower() not in {"radio.garden", "www.radio.garden"}:
                return None
            if match := _LISTEN_URL_RE.search(parsed.path):
                return match.group(1)
            return None
        if _CHANNEL_ID_RE.match(value):
            return value
        return None

    async def _pick_random_station(self) -> tuple[str, str]:
        places_payload = await self._fetch_json(f"{RADIO_API_BASE}/ara/content/places")
        places = (places_payload or {}).get("data", {}).get("list") or []
        if not places:
            raise ValueError("No radio places available.")

        random_places = places[:]
        shuffle(random_places)
        for place in random_places[: min(len(random_places), 5)]:
            place_id = place.get("id")
            if not place_id:
                continue

            channels = await self._fetch_place_channels(place_id)
            if not channels:
                continue

            station = choice(channels)
            if not (channel_id := self._channel_id_from_href(station.get("href") or station.get("url"))):
                continue
            title = station.get("title") or "Unknown Station"
            return channel_id, title

        raise ValueError("Could not find a random radio station. Try again.")

    async def _fetch_place_channels(self, place_id: str) -> list[dict]:
        payload = await self._fetch_json(f"{RADIO_API_BASE}/ara/content/page/{place_id}/channels")
        content = (payload or {}).get("data", {}).get("content") or []
        if not content:
            return []
        channels = []
        for item in content[0].get("items") or []:
            if channel := self._radio_station_page(item):
                channels.append(channel)
        return channels

    async def _fetch_radio_channel(self, channel_id: str) -> dict | None:
        payload = await self._fetch_json(f"{RADIO_API_BASE}/ara/content/channel/{channel_id}")
        return (payload or {}).get("data")

    async def _extract_stream_url_with_ytdlp(self, source_url: str) -> str:
        try:
            info = await get_running_loop().run_in_executor(None, self._search_source, source_url)
            if not info:
                raise ValueError("Failed to extract information.")
            if "entries" in info:
                if not info["entries"]:
                    raise ValueError("No results found.")
                info = info["entries"][0]
            if stream_url := info.get("url"):
                return stream_url
        except Exception as e:
            logger.error("yt-dlp extraction failed for %s: %s", source_url, e)
            raise ValueError("Could not resolve a playable radio stream.") from e

        raise ValueError("Could not resolve a playable radio stream.")

    async def _resolve_radio_stream_url(self, channel_id: str) -> str:
        stream_api_url = f"{RADIO_API_BASE}/ara/content/listen/{channel_id}/channel.mp3"
        if self.bot.session is None:
            raise RuntimeError("HTTP session is not available.")

        try:
            async with self.bot.session.get(stream_api_url, allow_redirects=False, timeout=10) as resp:
                redirect_statuses = {301, 302, 303, 307, 308}
                if resp.status in redirect_statuses:
                    location = resp.headers.get("Location")
                    if location:
                        return urljoin(stream_api_url, location)
                if resp.status == 200:
                    return stream_api_url
        except Exception as e:
            logger.error("HTTP request failed for %s: %s", stream_api_url, e)
            raise ValueError("Could not resolve a playable radio stream.") from e

        raise ValueError("Could not resolve a playable radio stream.")

    async def _search_radio_channel(self, query: str, region: str | None = None) -> dict | None:
        # Optional region hint narrows plain-text channel search results.
        search_query = query.strip()
        if region and region.strip():
            search_query = f"{search_query} {region.strip()}"
        payload = await self._fetch_json(f"{RADIO_API_BASE}/search", params={"q": search_query})
        hits = (payload or {}).get("hits", {}).get("hits") or []
        region_match: dict | None = None
        for hit in hits:
            source = hit.get("_source") or {}
            channel = self._radio_station_page(source)
            if not channel:
                continue
            if self._channel_id_from_href(channel.get("url")):
                if region and self._matches_region(channel, region):
                    return channel
                if region_match is None:
                    region_match = channel
                if not region:
                    return channel
        if region:
            return None
        return region_match

    @staticmethod
    def _radio_station_page(source: dict) -> dict | None:
        page = source.get("page")
        if isinstance(page, dict):
            return page if page.get("type") == "channel" else None
        return source if source.get("type") == "channel" else None

    @staticmethod
    def _matches_region(source: dict, region: str) -> bool:
        region_value = region.strip().lower()
        if not region_value:
            return True
        subtitle = str(source.get("subtitle") or "").lower()
        title = str(source.get("title") or "").lower()
        place = source.get("place") if isinstance(source.get("place"), dict) else {}
        country = source.get("country") if isinstance(source.get("country"), dict) else {}
        place_title = str(place.get("title") or "").lower()
        country_title = str(country.get("title") or "").lower()
        return region_value in subtitle or region_value in title or region_value in place_title or region_value in country_title

    async def _fetch_json(self, url: str, *, params: dict | None = None) -> dict | None:
        if self.bot.session is None:
            raise RuntimeError("HTTP session is not available.")
        try:
            async with self.bot.session.get(url, params=params, timeout=10) as resp:
                if resp.status != 200:
                    return None
                return await resp.json(content_type=None)
        except Exception as e:
            logger.error("HTTP request failed for %s: %s", url, e)
            return None

    @staticmethod
    def _channel_id_from_href(href: str | None) -> str | None:
        if not href:
            return None
        if match := _LISTEN_URL_RE.search(href):
            return match.group(1)
        segments = [seg for seg in href.split("/") if seg]
        if segments and _CHANNEL_ID_RE.match(segments[-1]):
            return segments[-1]
        return None

    @app_commands.command(
        name="stop",
        description="Stop the currently playing audio and disconnect."
    )
    async def stop(self, interaction: Interaction):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if await self._ensure_user_in_same_voice_channel(interaction, guild_id) is None:
            return
        await self._disconnect_and_cleanup(guild_id)
        await interaction.response.send_message(":stop_button: Stopped and disconnected.")

    @app_commands.command(
        name="pause",
        description="Pause the currently playing audio."
    )
    async def pause(self, interaction: Interaction):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if (vc := await self._ensure_user_in_same_voice_channel(interaction, guild_id)) is None:
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message(":pause_button: Playback paused.")
        else:
            await interaction.response.send_message(":x: Nothing is currently playing.", ephemeral=True)

    @app_commands.command(
        name="resume",
        description="Resume paused audio."
    )
    async def resume(self, interaction: Interaction):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if (vc := await self._ensure_user_in_same_voice_channel(interaction, guild_id)) is None:
            return
        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message(":arrow_forward: Playback resumed.")
        else:
            await interaction.response.send_message(":x: Playback is not paused.", ephemeral=True)

    @app_commands.command(
        name="queue",
        description="Show the current music queue. Displays up to 10 items and indicates if there are more."
    )
    async def queue(self, interaction: Interaction):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return

        max_display = 10
        queue_items = []
        if guild_id in self.currently_playing:
            _, title, duration = self.currently_playing[guild_id]
            queue_items.append(f"**Now Playing:** {title} [{duration}]")

        if guild_id in self.queues and self.queues[guild_id]:
            for i, (_, title, duration) in enumerate(self.queues[guild_id][:max_display]):
                queue_items.append(f"{i+1}. {title} [{duration}]")

            if len(self.queues[guild_id]) > max_display:
                queue_items.append(f"\n...and {len(self.queues[guild_id]) - max_display} more.")

        if not queue_items:
            await interaction.response.send_message(":x: The music queue is currently empty.")
        else:
            embed = Embed(
                title=":notes: Music Queue",
                description="\n".join(queue_items),
                color=self.bot.color,
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="skip",
        description="Skip the current song."
    )
    async def skip(self, interaction: Interaction):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if (vc := await self._ensure_user_in_same_voice_channel(interaction, guild_id)) is None:
            return
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await interaction.response.send_message(":track_next: Skipped.")
        else:
            await interaction.response.send_message(":x: Nothing is currently playing.", ephemeral=True)

    @app_commands.command(
        name="shuffle",
        description="Shuffle the current music queue."
    )
    async def shuffle(self, interaction: Interaction):
        if (guild_id := interaction.guild_id) is None:
            await interaction.response.send_message(":x: Could not determine guild ID.", ephemeral=True)
            return
        if guild_id in self.queues and self.queues[guild_id]:
            shuffle(self.queues[guild_id])
            await interaction.response.send_message(":twisted_rightwards_arrows: Queue shuffled.")
        else:
            await interaction.response.send_message(":x: The music queue is currently empty.", ephemeral=True)


async def setup(bot: "UiPy"):
    """Add the AudioCog to the bot."""
    await bot.add_cog(AudioCog(bot))
