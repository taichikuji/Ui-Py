from collections import deque
from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from functions.tool.audio import AudioCog, RadioCog


def _radio_command(name: str):
    return getattr(RadioCog, name)


def test_radio_subcommand_option_contracts():
    search = _radio_command("search")
    balloon = _radio_command("balloon")

    assert [(param.name, param.required) for param in search.parameters] == [
        ("query", True),
        ("region", False),
    ]
    assert balloon.parameters == []


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
    def __init__(self, payload, status=200, headers=None):
        self.payload = payload
        self.status = status
        self.headers = headers or {}

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

    def get(self, url, params=None, timeout=10, **kwargs):
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
        channel=SimpleNamespace(send=AsyncMock()),
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
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


def test_play_next_returns_without_voice_client(monkeypatch):
    cog = AudioCog(_make_bot())
    monkeypatch.setattr("functions.tool.audio.run_coroutine_threadsafe", lambda coro, _loop: coro.close())
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

    channel_id, title = await cog._resolve_radio_station("sFtKSe5I", "Barcelona")

    assert channel_id == "sFtKSe5I"
    assert title == "Mataro Radio"


@pytest.mark.asyncio
async def test_resolve_radio_station_falls_back_to_search():
    session = DummySession(
        [
            {"data": None},
            {
                "hits": {
                    "hits": [
                        {"_source": {"type": "place", "title": "Barcelona", "url": "/map/barcelona"}},
                        {
                            "_source": {
                                "type": "channel",
                                "page": {
                                    "type": "channel",
                                    "title": "Flaixbac",
                                    "subtitle": "Madrid, Spain",
                                    "url": "/listen/flaixbac/aaaa1111",
                                    "place": {"title": "Madrid"},
                                    "country": {"title": "Spain"},
                                },
                            }
                        },
                        {
                            "_source": {
                                "type": "channel",
                                "page": {
                                    "type": "channel",
                                    "title": "Flaixbac",
                                    "subtitle": "Barcelona, Spain",
                                    "url": "/listen/flaixbac/sFtKSe5I",
                                    "place": {"title": "Barcelona"},
                                    "country": {"title": "Spain"},
                                },
                            }
                        },
                    ]
                }
            },
        ]
    )
    cog = AudioCog(_make_bot(session=session))

    channel_id, title = await cog._resolve_radio_station("FlaixBac", "Barcelona")

    assert channel_id == "sFtKSe5I"
    assert title == "Flaixbac"
    assert session.calls[1][1] == {"q": "FlaixBac Barcelona"}


@pytest.mark.asyncio
async def test_resolve_radio_station_with_region_only_uses_region_search():
    session = DummySession(
        [
            {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "type": "channel",
                                "page": {
                                    "type": "channel",
                                    "title": "Radio Marca",
                                    "subtitle": "Madrid, Spain",
                                    "url": "/listen/radio-marca/spain123",
                                    "place": {"title": "Madrid"},
                                    "country": {"title": "Spain"},
                                },
                            }
                        },
                    ]
                }
            },
        ]
    )
    cog = AudioCog(_make_bot(session=session))

    channel_id, title = await cog._resolve_radio_station(None, "Spain")

    assert channel_id == "spain123"
    assert title == "Radio Marca"
    assert session.calls[0][1] == {"q": "Spain"}


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
                        {
                            "_source": {
                                "type": "channel",
                                "page": {
                                    "type": "channel",
                                    "title": "Flaixbac",
                                    "subtitle": "Madrid, Spain",
                                    "url": "/listen/flaixbac/sFtKSe5I",
                                    "place": {"title": "Madrid"},
                                    "country": {"title": "Spain"},
                                },
                            }
                        },
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
            {
                "data": {
                    "content": [
                        {
                            "items": [
                                {
                                    "page": {
                                        "type": "channel",
                                        "title": "Mataro Radio",
                                        "url": "/listen/mataroradio/sFtKSe5I",
                                    }
                                }
                            ]
                        }
                    ]
                }
            },
        ]
    )
    cog = AudioCog(_make_bot(session=session))

    channel_id, title = await cog._pick_random_station()

    assert channel_id == "sFtKSe5I"
    assert title == "Mataro Radio"


@pytest.mark.asyncio
async def test_resolve_radio_stream_url_prefers_redirect_location():
    session = DummySession([DummyResponse({}, status=302, headers={"Location": "https://stream.test/live"})])
    cog = AudioCog(_make_bot(session=session))

    stream_url = await cog._resolve_radio_stream_url("sFtKSe5I")

    assert stream_url == "https://stream.test/live"


@pytest.mark.asyncio
async def test_extract_stream_url_with_ytdlp_returns_stream_url(monkeypatch):
    cog = AudioCog(_make_bot())
    monkeypatch.setattr("functions.tool.audio.get_running_loop", lambda: DummyLoop({"url": "https://stream.test/live"}))

    stream_url = await cog._extract_stream_url_with_ytdlp("https://radio.garden/api/ara/content/listen/sFtKSe5I/channel.mp3")

    assert stream_url == "https://stream.test/live"


@pytest.mark.asyncio
async def test_extract_stream_url_with_ytdlp_raises_when_missing_stream_url(monkeypatch):
    cog = AudioCog(_make_bot())
    monkeypatch.setattr("functions.tool.audio.get_running_loop", lambda: DummyLoop({"webpage_url": "https://example.test"}))

    with pytest.raises(ValueError):
        await cog._extract_stream_url_with_ytdlp("https://radio.garden/api/ara/content/listen/sFtKSe5I/channel.mp3")


@pytest.mark.asyncio
async def test_resolve_radio_stream_url_raises_when_unplayable_status():
    session = DummySession([DummyResponse({}, status=403)])
    cog = AudioCog(_make_bot(session=session))

    with pytest.raises(ValueError):
        await cog._resolve_radio_stream_url("sFtKSe5I")


@pytest.mark.asyncio
async def test_radio_does_not_join_voice_when_station_resolution_fails(monkeypatch):
    connected_client = DummyVoiceClient(connected=True)
    voice_channel = DummyVoiceChannel(connected_client=connected_client)
    interaction = _make_interaction(user=DummyMember(42, voice_channel=voice_channel), guild_id=1)
    cog = AudioCog(_make_bot())
    cog._resolve_radio_station = AsyncMock(side_effect=ValueError("No radio station found for that query."))
    cog._resolve_radio_stream_url = AsyncMock()
    cog._get_or_connect_voice_client = AsyncMock()
    radio = RadioCog(cog)
    monkeypatch.setattr("functions.tool.audio.Member", DummyMember)

    await _radio_command("search").callback(radio, interaction, query="missing", region=None)

    cog._resolve_radio_station.assert_awaited_once_with("missing", None)
    cog._resolve_radio_stream_url.assert_not_awaited()
    cog._get_or_connect_voice_client.assert_not_awaited()
    voice_channel.connect.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(
        ":x: No radio station found for that query.",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_radio_does_not_join_voice_when_stream_resolution_fails(monkeypatch):
    connected_client = DummyVoiceClient(connected=True)
    voice_channel = DummyVoiceChannel(connected_client=connected_client)
    interaction = _make_interaction(user=DummyMember(42, voice_channel=voice_channel), guild_id=1)
    cog = AudioCog(_make_bot())
    cog._resolve_radio_station = AsyncMock(return_value=("sFtKSe5I", "Flaixbac"))
    cog._extract_stream_url_with_ytdlp = AsyncMock(side_effect=ValueError("Could not resolve a playable radio stream."))
    cog._resolve_radio_stream_url = AsyncMock(side_effect=ValueError("Could not resolve a playable radio stream."))
    cog._get_or_connect_voice_client = AsyncMock()
    radio = RadioCog(cog)
    monkeypatch.setattr("functions.tool.audio.Member", DummyMember)

    await _radio_command("search").callback(radio, interaction, query="flaixbac", region=None)

    cog._resolve_radio_station.assert_awaited_once_with("flaixbac", None)
    cog._extract_stream_url_with_ytdlp.assert_awaited_once_with("https://radio.garden/api/ara/content/listen/sFtKSe5I/channel.mp3")
    cog._resolve_radio_stream_url.assert_awaited_once_with("sFtKSe5I")
    cog._get_or_connect_voice_client.assert_not_awaited()
    voice_channel.connect.assert_not_awaited()
    interaction.followup.send.assert_awaited_once_with(
        ":x: Could not resolve a playable radio stream.",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_radio_balloon_uses_random_station_path(monkeypatch):
    connected_client = DummyVoiceClient(connected=True)
    voice_channel = DummyVoiceChannel(connected_client=connected_client)
    interaction = _make_interaction(user=DummyMember(42, voice_channel=voice_channel), guild_id=1)
    cog = AudioCog(_make_bot())
    cog._resolve_radio_station = AsyncMock(return_value=("sFtKSe5I", "Flaixbac"))
    cog._extract_stream_url_with_ytdlp = AsyncMock(return_value="https://stream.test/live")
    cog._enqueue_or_play = AsyncMock()
    radio = RadioCog(cog)
    monkeypatch.setattr("functions.tool.audio.Member", DummyMember)

    await _radio_command("balloon").callback(radio, interaction)

    cog._resolve_radio_station.assert_awaited_once_with(None, None)
    cog._enqueue_or_play.assert_awaited_once()


@pytest.mark.asyncio
async def test_play_connects_before_enqueue(monkeypatch):
    connected_client = DummyVoiceClient(connected=True)
    voice_channel = DummyVoiceChannel(connected_client=connected_client)
    interaction = _make_interaction(user=DummyMember(42, voice_channel=voice_channel), guild_id=1)
    cog = AudioCog(_make_bot())
    cog._enqueue_or_play = AsyncMock()
    monkeypatch.setattr("functions.tool.audio.Member", DummyMember)
    monkeypatch.setattr(
        "functions.tool.audio.get_running_loop",
        lambda: DummyLoop(
            {
                "url": "https://stream.test/live",
                "webpage_url": "https://youtube.test/watch?v=abc",
                "title": "Track",
                "duration_string": "3:00",
            }
        ),
    )

    await AudioCog.play.callback(cog, interaction, query="track")

    voice_channel.connect.assert_awaited_once()
    assert cog.voice_clients[1] is connected_client
    cog._enqueue_or_play.assert_awaited_once()


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
async def test_enqueue_or_play_rejects_when_queue_is_full():
    vc = DummyVoiceClient(connected=True, playing=True)
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = vc
    cog.queues[1] = deque([("u", "t", "d", None)] * 25)
    followup = AsyncMock()

    await cog._enqueue_or_play(
        1,
        source_url="https://youtube.test/watch?v=abc",
        title="Track",
        duration="3:00",
        stream_url="https://stream.test/live",
        followup=followup,
    )

    followup.assert_awaited_once_with(
        ":x: Queue is full (25 items).",
        ephemeral=True,
    )
    assert len(cog.queues[1]) == 25


@pytest.mark.asyncio
async def test_queue_displays_queued_items():
    interaction = _make_interaction(user=object(), guild_id=1)
    cog = AudioCog(_make_bot())
    cog.queues[1] = deque([("url", "Queued Track", "3:00", None)])

    await AudioCog.queue.callback(cog, interaction)

    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.description == "1. Queued Track [3:00]"


@pytest.mark.asyncio
async def test_disconnect_and_cleanup_clears_all_state():
    vc = DummyVoiceClient(connected=True, playing=True)
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = vc
    cog.queues[1] = deque([("u", "t", "d", None)])
    cog.currently_playing[1] = ("u", "t", "d")
    cog.command_channels[1] = object()

    await cog._disconnect_and_cleanup(1)

    vc.stop.assert_called_once()
    vc.disconnect.assert_awaited_once()
    assert cog.voice_clients == {}
    assert cog.queues == {}
    assert cog.currently_playing == {}
    assert cog.command_channels == {}


@pytest.mark.asyncio
async def test_play_next_pulls_from_queue(monkeypatch):
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = DummyVoiceClient(connected=True)
    cog.queues[1] = deque([("url", "title", "3:00", None)])
    cog._play_next_track_and_announce = AsyncMock()
    scheduled = []

    def fake_run(coro, _loop):
        scheduled.append(coro)

    monkeypatch.setattr("functions.tool.audio.run_coroutine_threadsafe", fake_run)
    cog._play_next(1)
    await scheduled[0]

    cog._play_next_track_and_announce.assert_awaited_once_with(1, "url", "title", "3:00", None)
    assert cog.queues[1] == deque()


@pytest.mark.asyncio
async def test_play_next_cleans_state_when_voice_disconnected(monkeypatch):
    cog = AudioCog(_make_bot())
    cog.voice_clients[1] = DummyVoiceClient(connected=False)
    cog.queues[1] = deque([("u", "t", "d", None)])
    cog.currently_playing[1] = ("u", "t", "d")
    cog.command_channels[1] = object()
    scheduled = []

    def fake_run(coro, _loop):
        scheduled.append(coro)

    monkeypatch.setattr("functions.tool.audio.run_coroutine_threadsafe", fake_run)
    cog._play_next(1)
    await scheduled[0]

    assert cog.voice_clients == {}
    assert cog.queues == {}
    assert cog.currently_playing == {}
    assert cog.command_channels == {}
