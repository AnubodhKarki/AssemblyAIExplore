import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
BASE_URL = "https://api.assemblyai.com"
DEFAULT_AUDIO_URL = "https://storage.googleapis.com/aai-docs-samples/sports_injuries.mp3"

LANGUAGE_OPTIONS = {
    "English (US)": "en_us",
    "English (UK)": "en_uk",
    "English (AU)": "en_au",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Chinese": "zh",
    "Japanese": "ja",
    "Hindi": "hi",
    "Auto-detect": None,
}

MODEL_OPTIONS = {
    "Best (Universal-3 Pro)": "universal-3-pro",
    "Nano (Universal-2)": "universal-2",
}

STREAMING_MODEL_OPTIONS = {
    "Universal-3 Pro Streaming (u3-rt-pro)": "u3-rt-pro",
    "Universal Streaming Multilingual": "universal-streaming-multilingual",
    "Universal Streaming English": "universal-streaming-english",
    "Whisper Streaming (99+ langs)": "whisper-rt",
}


def auth_headers() -> dict:
    return {"authorization": API_KEY}
