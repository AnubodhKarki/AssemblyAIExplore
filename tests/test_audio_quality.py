import io
import wave

from assemblyai_explorer.audio_quality import analyze_uploaded_audio, analyze_url_metadata


def _make_wav_bytes(*, sample_rate: int, duration_s: float, channels: int = 1, sample_width: int = 2) -> bytes:
    frame_count = int(sample_rate * duration_s)
    silence_frame = b"\x00" * sample_width * channels
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(silence_frame * frame_count)
        return buf.getvalue()


def test_analyze_uploaded_audio_wav_detects_basic_quality_warnings():
    wav_bytes = _make_wav_bytes(sample_rate=8000, duration_s=2.0)
    report = analyze_uploaded_audio(file_name="clip.wav", file_type="audio/wav", file_bytes=wav_bytes)

    assert report["label"] in {"poor", "fair"}
    assert report["metrics"]["format"] == "wav"
    assert report["metrics"]["sample_rate_hz"] == 8000
    assert report["metrics"]["duration_seconds"] == 2.0
    assert any("Short audio" in warning for warning in report["warnings"])
    assert any("Low sample rate" in warning for warning in report["warnings"])


def test_analyze_uploaded_audio_non_wav_is_best_effort():
    report = analyze_uploaded_audio(file_name="clip.mp3", file_type="audio/mpeg", file_bytes=b"\x00" * 2048)

    assert report["metrics"]["format"] == "mp3"
    assert report["metrics"]["duration_seconds"] is None
    assert any("WAV uploads only" in warning for warning in report["warnings"])


def test_analyze_url_metadata_flags_non_audio_content_type():
    report = analyze_url_metadata(
        url="https://example.com/file.txt",
        probe={
            "reachable": True,
            "status_code": 200,
            "headers": {
                "content_type": "text/plain",
                "content_length_bytes": 50_000,
                "accept_ranges": "bytes",
            },
        },
    )

    assert report["metrics"]["http_status"] == 200
    assert any("Content-Type" in warning for warning in report["warnings"])
    assert any("Very small content-length" in warning for warning in report["warnings"])
