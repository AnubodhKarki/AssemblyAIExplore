import queue
from types import SimpleNamespace

from assemblyai_explorer.streaming import (
    build_streaming_parameters,
    drain_stream_events,
    format_input_device_label,
    is_input_overflow_error,
)


def test_drain_stream_events_applies_callback_updates():
    session_state = SimpleNamespace(
        _stream_events=queue.Queue(),
        live_transcript="",
        stream_session_id=None,
        stream_word_count=None,
        stream_audio_duration=None,
        stream_error=None,
        _stream_client=None,
        streaming=True,
    )
    client = object()

    session_state._stream_events.put(("session_id", "sess_123"))
    session_state._stream_events.put(("transcript_line", "hello world"))
    session_state._stream_events.put(("audio_duration", 2.5))
    session_state._stream_events.put(("client", client))
    session_state._stream_events.put(("stream_ended", None))

    drain_stream_events(session_state)

    assert session_state.stream_session_id == "sess_123"
    assert session_state.live_transcript == "hello world\n"
    assert session_state.stream_word_count == 2.5
    assert session_state.stream_audio_duration == 2.5
    assert session_state._stream_client is client
    assert session_state.streaming is False


def test_format_input_device_label_includes_identifying_fields():
    label = format_input_device_label(
        {
            "index": 3,
            "name": "Built-in Microphone",
            "default_sample_rate": 44100.0,
        }
    )

    assert label == "[3] Built-in Microphone (44100 Hz)"


def test_build_streaming_parameters_prefers_speech_model_field():
    class FakeStreamingParameters:
        model_fields = {"sample_rate": None, "encoding": None, "format_turns": None, "speech_model": None}

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAAI:
        class AudioEncoding:
            pcm_s16le = "pcm_s16le"

    params = build_streaming_parameters(FakeStreamingParameters, FakeAAI, "u3-rt-pro")
    assert params.kwargs["speech_model"] == "u3-rt-pro"
    assert "model" not in params.kwargs


def test_build_streaming_parameters_falls_back_to_model_field():
    class FakeStreamingParameters:
        model_fields = {"sample_rate": None, "encoding": None, "format_turns": None, "model": None}

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAAI:
        class AudioEncoding:
            pcm_s16le = "pcm_s16le"

    params = build_streaming_parameters(FakeStreamingParameters, FakeAAI, "u3-rt-pro")
    assert params.kwargs["model"] == "u3-rt-pro"
    assert "speech_model" not in params.kwargs


def test_is_input_overflow_error_matches_errno_and_message():
    assert is_input_overflow_error(OSError(-9981, "Input overflowed")) is True
    assert is_input_overflow_error(OSError(1, "input overflowed")) is True
    assert is_input_overflow_error(OSError(1, "something else")) is False
