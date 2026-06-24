from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from functions.tool.audio import AudioCog


class DummyMember:
    def __init__(self, user_id: int, *, voice_channel=None):
        self.id = user_id
        self.voice = None if voice_channel is None else SimpleNamespace(channel=voice_channel)


class DummyVoiceChannel:
    def __init__(self, connected_client=None):
        self.connect = AsyncMock(return_value=connected_client)


class DummyVoiceClient:
    def __init__(self, *, connected=True, playing=False, paused=False, channel=None):
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


class DummyResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        return self.payload


class DummySession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url, params=None, timeout=10):
        self.calls.append((url, params))
        payload = self.responses.pop(0)
        if isinstance(payload, DummyResponse):
            return payload
        return DummyResponse(payload)


def _make_bot(*, session=None):
    return SimpleNamespace(loop=object(), color=0x123456, session=session)


def _make_interaction(*, user, guild_id=1):
    return SimpleNamespace(
        guild_id=guild_id,
        user=user,
        response=SimpleNamespace(send_message=AsyncMock()),
    )


@pytest.mark.asyncio
async def test_play_song_returns_false_when_refreshed_stream_url_missing(monkeypatch):
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = DummyVoiceClient(connected=True)
    cog._play_next = MagicMock()
    monkeypatch.setattr("functions.tool.audio.get_running_loop", lambda: DummyLoop({"webpage_url": "x"}))

    started = await cog._play_song(1, "https://example.test/watch", None, "Track", "3:00")

    assert started is False
    cog._play_next.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_play_song_starts_playback_and_tracks_current_song(monkeypatch):
    vc = DummyVoiceClient(connected=True)
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = vc
    monkeypatch.setattr("functions.tool.audio.FFmpegPCMAudio", lambda stream_url, **_kw: f"audio:{stream_url}")

    started = await cog._play_song(1, "https://example.test/watch", "https://stream.test", "Track", "3:00")

    assert started is True
    assert cog.currently_playing[1] == ("https://example.test/watch", "Track", "3:00")
    assert vc.play.call_args.args[0] == "audio:https://stream.test"


@pytest.mark.asyncio
async def test_ensure_user_in_same_voice_channel_rejects_other_channel(monkeypatch):
    cog = AudioCog(_make_bot())
    bot_channel = object()
    other_channel = object()
    cog.voice_clients[1] = DummyVoiceClient(connected=True, channel=bot_channel)
    monkeypatch.setattr("functions.tool.audio.Member", DummyMember)
    interaction = _make_interaction(user=DummyMember(42, voice_channel=other_channel), guild_id=1)

    vc = await cog._ensure_user_in_same_voice_channel(interaction, 1)

    assert vc is None
    interaction.response.send_message.assert_awaited_with(
        ":x: You must be in the same voice channel as the bot to use this command.",
        ephemeral=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("command", [AudioCog.stop, AudioCog.pause, AudioCog.resume, AudioCog.skip])
async def test_control_commands_return_early_when_same_channel_check_fails(command):
    interaction = _make_interaction(user=object(), guild_id=1)
    cog = AudioCog(_make_bot())
    cog._ensure_user_in_same_voice_channel = AsyncMock(return_value=None)
    cog._disconnect_and_cleanup = AsyncMock()

    await command.callback(cog, interaction)

    cog._ensure_user_in_same_voice_channel.assert_awaited_once_with(interaction, 1)
    interaction.response.send_message.assert_not_awaited()
    cog._disconnect_and_cleanup.assert_not_awaited()


def test_play_next_returns_without_voice_client():
    cog = AudioCog(_make_bot())
    cog._play_next(123)
    assert cog.currently_playing == {}


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://radio.garden/listen/mataroradio/sFtKSe5I", "sFtKSe5I"),
        ("http://radio.garden/listen/esplugues-fm/cKnK9OEm", "cKnK9OEm"),
        ("sFtKSe5I", "sFtKSe5I"),
        ("flaixbac", "flaixbac"),
        ("https://other.site/listen/foo/sFtKSe5I", None),
    ],
)
def test_extract_channel_id(value, expected):
    assert AudioCog._extract_channel_id(value) == expected


@pytest.mark.parametrize(
    "href, expected",
    [
        ("/listen/kutx-98-9/vbFsCngB", "vbFsCngB"),
        ("/listen/foo/sFtKSe5I", "sFtKSe5I"),
        ("/something/else/", None),
    ],
)
def test_channel_id_from_href(href, expected):
    assert AudioCog._channel_id_from_href(href) == expected


@pytest.mark.asyncio
async def test_resolve_radio_station_with_channel_id():
    session = DummySession([{"data": {"title": "Mataro Radio", "url": "/listen/mataroradio/sFtKSe5I"}}])
    cog = AudioCog(_make_bot(session=session))

    channel_id, title, listen_url = await cog._resolve_radio_station("sFtKSe5I", "Barcelona")

    assert channel_id == "sFtKSe5I"
    assert title == "Mataro Radio"
    assert listen_url == "https://radio.garden/listen/mataroradio/sFtKSe5I"


@pytest.mark.asyncio
async def test_resolve_radio_station_falls_back_to_search():
    session = DummySession(
        [
            {"data": None},
            {
                "hits": {
                    "hits": [
                        {"_source": {"type": "place", "title": "Barcelona", "url": "/map/barcelona"}},
                        {"_source": {"type": "channel", "title": "Flaixbac", "subtitle": "Madrid, Spain", "url": "/listen/flaixbac/aaaa1111"}},
                        {"_source": {"type": "channel", "title": "Flaixbac", "subtitle": "Barcelona, Spain", "url": "/listen/flaixbac/sFtKSe5I"}},
                    ]
                }
            },
        ]
    )
    cog = AudioCog(_make_bot(session=session))

    channel_id, title, listen_url = await cog._resolve_radio_station("FlaixBac", "Barcelona")

    assert channel_id == "sFtKSe5I"
    assert title == "Flaixbac"
    assert listen_url == "https://radio.garden/listen/flaixbac/sFtKSe5I"
    assert session.calls[1][1] == {"q": "FlaixBac Barcelona"}


@pytest.mark.asyncio
async def test_resolve_radio_station_raises_when_search_empty():
    session = DummySession([{"hits": {"hits": []}}])
    cog = AudioCog(_make_bot(session=session))

    with pytest.raises(ValueError):
        await cog._resolve_radio_station("does-not-exist", "Barcelona")


@pytest.mark.asyncio
async def test_resolve_radio_station_raises_when_region_filter_has_no_match():
    session = DummySession(
        [
            {
                "hits": {
                    "hits": [
                        {"_source": {"type": "channel", "title": "Flaixbac", "subtitle": "Madrid, Spain", "url": "/listen/flaixbac/sFtKSe5I"}},
                    ]
                }
            }
        ]
    )
    cog = AudioCog(_make_bot(session=session))

    with pytest.raises(ValueError):
        await cog._resolve_radio_station("FlaixBac", "Barcelona")


@pytest.mark.asyncio
async def test_pick_random_station_returns_channel_from_random_place():
    session = DummySession(
        [
            {"data": {"list": [{"id": "place1"}]}},
            {"data": {"content": [{"items": [{"title": "Mataro Radio", "href": "/listen/mataroradio/sFtKSe5I"}]}]}},
        ]
    )
    cog = AudioCog(_make_bot(session=session))

    channel_id, title, listen_url = await cog._pick_random_station()

    assert channel_id == "sFtKSe5I"
    assert title == "Mataro Radio"
    assert listen_url == "https://radio.garden/listen/mataroradio/sFtKSe5I"


@pytest.mark.asyncio
async def test_pick_random_station_raises_when_no_places():
    session = DummySession([{"data": {"list": []}}])
    cog = AudioCog(_make_bot(session=session))

    with pytest.raises(ValueError):
        await cog._pick_random_station()


@pytest.mark.asyncio
async def test_enqueue_or_play_queues_when_playing():
    vc = DummyVoiceClient(connected=True, playing=True)
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = vc
    followup = AsyncMock()

    await cog._enqueue_or_play(
        1,
        source_url="https://radio.garden/listen/mataroradio/sFtKSe5I",
        title="Mataro Radio",
        duration="LIVE",
        stream_url="https://radio.garden/api/ara/content/listen/sFtKSe5I/channel.mp3",
        followup=followup,
    )

    assert cog.queues[1][0][1] == "Mataro Radio"
    followup.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_and_cleanup_clears_all_state():
    vc = DummyVoiceClient(connected=True, playing=True)
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = vc
    cog.queues[1] = [("u", "t", "d", None)]
    cog.currently_playing[1] = ("u", "t", "d")
    cog.command_channels[1] = object()

    await cog._disconnect_and_cleanup(1)

    vc.stop.assert_called_once()
    vc.disconnect.assert_awaited_once()
    assert cog.voice_clients == {}
    assert cog.queues == {}
    assert cog.currently_playing == {}
    assert cog.command_channels == {}


def test_play_next_pulls_from_queue_and_schedules():
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = DummyVoiceClient(connected=True)
    cog.queues[1] = [("url", "title", "3:00", None)]

    scheduled = []

    def fake_run(coro, _loop):
        scheduled.append(coro)
        coro.close()

    import functions.tool.audio as audio_mod

    original = audio_mod.run_coroutine_threadsafe
    audio_mod.run_coroutine_threadsafe = fake_run
    try:
        cog._play_next(1)
    finally:
        audio_mod.run_coroutine_threadsafe = original

    assert len(scheduled) == 1
    assert cog.queues[1] == []
