import time

import requests

from .config import BASE_URL, auth_headers


def check_api_health():
    """Validates the API key and measures round-trip latency. Returns (status_code, elapsed_ms, rate_limit_headers)."""
    t0 = time.perf_counter()
    resp = requests.get(f"{BASE_URL}/v2/transcript", params={"limit": 1}, headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    rate_headers = {k: v for k, v in resp.headers.items() if "ratelimit" in k.lower() or "x-request-id" in k.lower()}
    return resp.status_code, elapsed, rate_headers


def get_transcript_sentences(transcript_id: str):
    t0 = time.perf_counter()
    resp = requests.get(f"{BASE_URL}/v2/transcript/{transcript_id}/sentences", headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed


def get_transcript_paragraphs(transcript_id: str):
    t0 = time.perf_counter()
    resp = requests.get(f"{BASE_URL}/v2/transcript/{transcript_id}/paragraphs", headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed



def upload_file(file_bytes: bytes) -> str:
    resp = requests.post(
        f"{BASE_URL}/v2/upload",
        headers={**auth_headers(), "content-type": "application/octet-stream"},
        data=file_bytes,
    )
    resp.raise_for_status()
    return resp.json()["upload_url"]


def submit_transcript_debug(payload: dict):
    t0 = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/v2/transcript", json=payload, headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed


def poll_transcript_debug(transcript_id: str):
    data = {}
    status_code = 0
    elapsed = 0
    for _ in range(60):
        t0 = time.perf_counter()
        resp = requests.get(f"{BASE_URL}/v2/transcript/{transcript_id}", headers=auth_headers())
        elapsed = round((time.perf_counter() - t0) * 1000)
        status_code = resp.status_code
        data = resp.json()
        if data.get("status") in ("completed", "error"):
            return data, status_code, elapsed
        time.sleep(3)
    return {"status": "error", "error": "Timed out."}, status_code, elapsed


def get_transcript(transcript_id: str):
    t0 = time.perf_counter()
    resp = requests.get(f"{BASE_URL}/v2/transcript/{transcript_id}", headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed, dict(resp.headers)


def list_transcripts(limit: int):
    t0 = time.perf_counter()
    resp = requests.get(f"{BASE_URL}/v2/transcript", params={"limit": limit}, headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed


def delete_transcript(transcript_id: str):
    t0 = time.perf_counter()
    resp = requests.delete(f"{BASE_URL}/v2/transcript/{transcript_id}", headers=auth_headers())
    elapsed = round((time.perf_counter() - t0) * 1000)
    return resp.json(), resp.status_code, elapsed
