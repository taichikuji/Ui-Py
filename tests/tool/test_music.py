from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from functions.tool.music import MusicCog


class DummyMember:
    def __init__(self, user_id: int, *, voice_channel=None):
        self.id = user_id
        self.voice = None if voice_channel is None else SimpleNamespace(channel=voice_channel)


class DummyTextChannel:
    pass


class DummyVoiceChannel:
    def __init__(self, connected_client=None):
        self._client = connected_client
        self.connect = AsyncMock(return_value=connected_client)


class DummyVoiceClient:
    def __init__(self, *, connected: bool = True, playing: bool = False, paused: bool = False, channel=None):
        self._connected = connected
        self._playing = playing
        self._paused = paused
        self.channel = channel
        self.play = MagicMock()
        self.pause = MagicMock()
        self.resume = MagicMock()
        self.stop = MagicMock()
        self.disconnect = AsyncMock()

    def is_connected(self):
        return self._connected

    def is_playing(self):
        return self._playing

    def is_paused(self):
        return self._paused


class DummyLoop:
    def __init__(self, result):
        self.result = result

    async def run_in_executor(self, _executor, _fn, _arg):
        return self.result


def _make_interaction(*, user, guild_id: int = 1, channel=None):
    return SimpleNamespace(
        guild_id=guild_id,
        user=user,
        channel=channel,
        response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


@pytest.mark.asyncio
async def test_play_song_returns_false_when_refreshed_stream_url_missing(monkeypatch):
    bot = SimpleNamespace(loop=object(), color=0x123456)
    cog = MusicCog(bot)
    cog.voice_clients[1] = DummyVoiceClient(connected=True)
    cog._play_next = MagicMock()

    monkeypatch.setattr("functions.tool.music.get_running_loop", lambda: DummyLoop({"webpage_url": "x"}))

    started = await cog._play_song(1, "https://example.test/watch", None, "Track", "3:00")

    assert started is False
    cog._play_next.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_play_song_returns_false_when_voice_client_missing(monkeypatch):
    bot = SimpleNamespace(loop=object(), color=0x123456)
    cog = MusicCog(bot)
    monkeypatch.setattr("functions.tool.music.get_running_loop", lambda: DummyLoop({"url": "https://stream.test"}))

    started = await cog._play_song(1, "https://example.test/watch", None, "Track", "3:00")

    assert started is False


@pytest.mark.asyncio
async def test_play_song_starts_playback_and_tracks_current_song(monkeypatch):
    bot = SimpleNamespace(loop=object(), color=0x123456)
    vc = DummyVoiceClient(connected=True)
    cog = MusicCog(bot)
    cog.voice_clients[1] = vc

    monkeypatch.setattr(
        "functions.tool.music.FFmpegPCMAudio",
        lambda stream_url, **_kwargs: f"audio:{stream_url}",
    )

    started = await cog._play_song(1, "https://example.test/watch", "https://stream.test", "Track", "3:00")

    assert started is True
    assert cog.currently_playing[1] == ("https://example.test/watch", "Track", "3:00")
    vc.play.assert_called_once()
    assert vc.play.call_args.args[0] == "audio:https://stream.test"


@pytest.mark.asyncio
async def test_play_command_reports_failure_when_play_song_returns_false(monkeypatch):
    bot = SimpleNamespace(loop=object(), color=0x123456)
    vc = DummyVoiceClient(connected=True, playing=False, paused=False)
    voice_channel = DummyVoiceChannel(connected_client=vc)
    user = DummyMember(99, voice_channel=voice_channel)
    interaction_channel = DummyTextChannel()
    interaction = _make_interaction(user=user, channel=interaction_channel)
    cog = MusicCog(bot)
    cog._play_song = AsyncMock(return_value=False)

    monkeypatch.setattr("functions.tool.music.Member", DummyMember)
    monkeypatch.setattr("functions.tool.music.TextChannel", DummyTextChannel)
    monkeypatch.setattr("functions.tool.music.VoiceChannel", DummyVoiceChannel)
    monkeypatch.setattr(
        "functions.tool.music.get_running_loop",
        lambda: DummyLoop(
            {
                "url": "https://stream.test",
                "title": "Track",
                "duration_string": "3:00",
                "webpage_url": "https://example.test/watch",
            }
        ),
    )

    await MusicCog.play.callback(cog, interaction, "test query")

    interaction.followup.send.assert_awaited_with(
        ":x: Failed to start playback for that track.",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_ensure_user_in_same_voice_channel_rejects_other_channel(monkeypatch):
    bot = SimpleNamespace(loop=object(), color=0x123456)
    cog = MusicCog(bot)
    bot_channel = object()
    other_channel = object()
    cog.voice_clients[1] = DummyVoiceClient(connected=True, channel=bot_channel)

    monkeypatch.setattr("functions.tool.music.Member", DummyMember)
    interaction = _make_interaction(user=DummyMember(42, voice_channel=other_channel), guild_id=1)

    vc = await cog._ensure_user_in_same_voice_channel(interaction, 1)

    assert vc is None
    interaction.response.send_message.assert_awaited_with(
        ":x: You must be in the same voice channel as the bot to use this command.",
        ephemeral=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [MusicCog.stop, MusicCog.pause, MusicCog.resume, MusicCog.skip],
)
async def test_control_commands_return_early_when_same_channel_check_fails(command):
    bot = SimpleNamespace(loop=object(), color=0x123456)
    interaction = _make_interaction(user=object(), guild_id=1)
    cog = MusicCog(bot)
    cog._ensure_user_in_same_voice_channel = AsyncMock(return_value=None)
    cog._disconnect_and_cleanup = AsyncMock()

    await command.callback(cog, interaction)

    cog._ensure_user_in_same_voice_channel.assert_awaited_once_with(interaction, 1)
    interaction.response.send_message.assert_not_awaited()
    cog._disconnect_and_cleanup.assert_not_awaited()


def test_play_next_returns_without_voice_client():
    bot = SimpleNamespace(loop=object(), color=0x123456)
    cog = MusicCog(bot)

    cog._play_next(123)

    assert cog.currently_playing == {}
