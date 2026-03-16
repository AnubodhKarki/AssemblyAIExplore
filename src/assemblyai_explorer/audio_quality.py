import io
import os
import wave


def _quality_label(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 55:
        return "fair"
    return "poor"


def evaluate_quality(*, metrics: dict, warnings: list[str]) -> dict:
    score = 100
    for warning in warnings:
        if "short audio" in warning.lower():
            score -= 20
        elif "sample rate" in warning.lower():
            score -= 25
        elif "content-type" in warning.lower():
            score -= 30
        elif "very small" in warning.lower():
            score -= 10
        else:
            score -= 8
    score = max(score, 0)
    return {
        "score": score,
        "label": _quality_label(score),
        "warnings": warnings,
        "metrics": metrics,
    }


def analyze_uploaded_audio(*, file_name: str, file_type: str | None, file_bytes: bytes) -> dict:
    size_bytes = len(file_bytes)
    extension = os.path.splitext(file_name)[1].lower().lstrip(".")
    metrics = {
        "source_type": "upload",
        "file_name": file_name,
        "format": extension or "unknown",
        "mime_type": file_type or "unknown",
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "duration_seconds": None,
        "sample_rate_hz": None,
        "channels": None,
        "bitrate_kbps": None,
    }
    warnings: list[str] = []

    if extension == "wav":
        try:
            with wave.open(io.BytesIO(file_bytes), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_count = wav_file.getnframes()
                duration = frame_count / frame_rate if frame_rate else 0
                bitrate_kbps = round((frame_rate * channels * sample_width * 8) / 1000, 1) if frame_rate else None

            metrics["duration_seconds"] = round(duration, 2)
            metrics["sample_rate_hz"] = frame_rate
            metrics["channels"] = channels
            metrics["bitrate_kbps"] = bitrate_kbps

            if duration and duration < 5:
                warnings.append("Short audio (<5s) can reduce transcription context.")
            if frame_rate and frame_rate < 16000:
                warnings.append("Low sample rate (<16kHz) may reduce accuracy.")
            if channels and channels > 2:
                warnings.append("More than 2 channels detected; verify channel mapping.")
        except (wave.Error, EOFError):
            warnings.append("WAV header could not be parsed; verify that the file is a valid WAV.")
    else:
        warnings.append("Detailed duration/sample-rate checks are currently available for WAV uploads only.")
        if extension not in {"mp3", "m4a", "ogg", "mp4"}:
            warnings.append("Unrecognized upload format; verify codec/container compatibility.")

    if size_bytes < 100 * 1024:
        warnings.append("Very small file size; audio may be too short or silent.")

    return evaluate_quality(metrics=metrics, warnings=warnings)


def analyze_url_metadata(*, url: str, probe: dict) -> dict:
    headers = probe.get("headers") or {}
    content_type = headers.get("content_type") or "unknown"
    content_length = headers.get("content_length_bytes")
    metrics = {
        "source_type": "url",
        "url": url,
        "http_status": probe.get("status_code"),
        "content_type": content_type,
        "content_length_bytes": content_length,
        "content_length_mb": round(content_length / (1024 * 1024), 2) if isinstance(content_length, int) else None,
        "accept_ranges": headers.get("accept_ranges"),
    }

    warnings: list[str] = []
    if not probe.get("reachable"):
        warnings.append("URL probe failed; verify accessibility before transcription.")
    if content_type != "unknown" and not (
        content_type.startswith("audio/") or content_type.startswith("video/")
    ):
        warnings.append("Content-Type does not look like audio/video.")
    if isinstance(content_length, int) and content_length < 100 * 1024:
        warnings.append("Very small content-length; source may be too short.")
    if content_length is None:
        warnings.append("Content-Length unavailable; duration/bitrate cannot be estimated from headers.")

    return evaluate_quality(metrics=metrics, warnings=warnings)
