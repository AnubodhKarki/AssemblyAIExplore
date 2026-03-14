import time
from datetime import datetime

import streamlit as st

from .api import (
    check_api_health,
    delete_transcript,
    get_transcript,
    get_transcript_paragraphs,
    get_transcript_sentences,
    list_transcripts,
    poll_transcript_debug,
    submit_transcript_debug,
    upload_file,
)
from .config import API_KEY, DEFAULT_AUDIO_URL, LANGUAGE_OPTIONS, MODEL_OPTIONS, STREAMING_MODEL_OPTIONS
from .payloads import build_params_snapshot, build_transcript_payload
from .rendering import render_results
from .state import init_session_state
from .streaming import (
    drain_stream_events,
    format_input_device_label,
    list_input_devices,
    start_streaming_thread,
    stop_streaming,
    streaming_sdk_import,
)


def render_sidebar_history():
    with st.sidebar:
        st.header("History")
        if not st.session_state.history:
            st.caption("No transcriptions yet.")
        for item in reversed(st.session_state.history):
            with st.expander(f"{item['timestamp']} — {item['model']}"):
                st.write(f"**Source:** {item['audio_source']}")
                st.write(f"**ID:** `{item['id']}`")
                st.write(item["snippet"])
                if item.get("result"):
                    render_results(item["result"], item["params"], allow_expanders=False)


def render_prerecorded_tab():
    st.subheader("Audio Source")
    source_mode = st.radio("Input type", ["Default sample URL", "Paste a URL", "Upload a file"], horizontal=True)

    audio_url = None
    uploaded_file = None

    if source_mode == "Default sample URL":
        st.code(DEFAULT_AUDIO_URL)
        audio_url = DEFAULT_AUDIO_URL
    elif source_mode == "Paste a URL":
        audio_url = st.text_input("Audio URL", placeholder="https://...")
    else:
        uploaded_file = st.file_uploader("Upload audio/video file", type=["mp3", "wav", "m4a", "ogg", "mp4"])

    st.subheader("Model & Language")
    col1, col2 = st.columns(2)
    with col1:
        model_label = st.selectbox("Model", list(MODEL_OPTIONS.keys()))
        model = MODEL_OPTIONS[model_label]
    with col2:
        lang_label = st.selectbox("Language", list(LANGUAGE_OPTIONS.keys()))
        language_code = LANGUAGE_OPTIONS[lang_label]

    st.subheader("Features")
    c1, c2, c3 = st.columns(3)
    with c1:
        speaker_labels = st.checkbox("Speaker Labels")
        sentiment_analysis = st.checkbox("Sentiment Analysis")
        entity_detection = st.checkbox("Entity Detection")
    with c2:
        auto_highlights = st.checkbox("Key Phrases")
        iab_categories = st.checkbox("Topic Detection")
        filter_profanity = st.checkbox("Filter Profanity")
    with c3:
        punctuate = st.checkbox("Punctuation", value=True)
        format_text = st.checkbox("Format Text", value=True)
        disfluencies = st.checkbox("Include Filler Words")

    with st.expander("Advanced"):
        speakers_expected = st.number_input("Expected speakers (0 = auto)", min_value=0, max_value=20, value=0)
        keyterms_input = st.text_area("Keyterms (comma-separated)", placeholder="opal, Oprah Winfrey, ...")
        prompt_input = st.text_area("Context prompt (up to 1500 words)", placeholder="This is an interview about...")

    if not st.button("Transcribe", type="primary"):
        return

    resolved_url = None
    audio_source_label = ""

    if source_mode == "Upload a file":
        if not uploaded_file:
            st.warning("Please upload a file.")
            return
        with st.spinner("Uploading file..."):
            resolved_url = upload_file(uploaded_file.read())
        audio_source_label = uploaded_file.name
    elif source_mode == "Paste a URL":
        if not audio_url:
            st.warning("Please enter a URL.")
            return
        resolved_url = audio_url
        audio_source_label = audio_url
    else:
        resolved_url = DEFAULT_AUDIO_URL
        audio_source_label = "default sample"

    payload = build_transcript_payload(
        audio_url=resolved_url,
        model=model,
        language_code=language_code,
        punctuate=punctuate,
        format_text=format_text,
        speaker_labels=speaker_labels,
        speakers_expected=speakers_expected,
        sentiment_analysis=sentiment_analysis,
        entity_detection=entity_detection,
        auto_highlights=auto_highlights,
        iab_categories=iab_categories,
        filter_profanity=filter_profanity,
        disfluencies=disfluencies,
        keyterms_input=keyterms_input,
        prompt_input=prompt_input,
    )

    params_snapshot = build_params_snapshot(
        speaker_labels=speaker_labels,
        sentiment_analysis=sentiment_analysis,
        entity_detection=entity_detection,
        auto_highlights=auto_highlights,
        iab_categories=iab_categories,
    )

    with st.expander("Request payload (JSON)", expanded=False):
        st.json(payload)

    with st.spinner("Submitting..."):
        submit_json, submit_status, submit_ms = submit_transcript_debug(payload)

    st.caption(f"Submit — HTTP {submit_status} · {submit_ms} ms")

    if submit_status >= 400:
        st.error(f"Submission failed (HTTP {submit_status}):")
        st.json(submit_json)
        return

    transcript_id = submit_json["id"]
    st.info(f"Transcript ID: `{transcript_id}` — polling for results...")

    with st.spinner("Transcribing..."):
        result, poll_status, poll_ms = poll_transcript_debug(transcript_id)

    st.caption(f"Final poll — HTTP {poll_status} · {poll_ms} ms")

    with st.expander("Raw JSON response", expanded=False):
        st.json(result)

    text = result.get("text") or ""
    snippet = text[:120] + ("..." if len(text) > 120 else "")

    st.session_state.history.append(
        {
            "id": transcript_id,
            "audio_source": audio_source_label,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "model": model_label,
            "snippet": snippet,
            "result": result,
            "params": params_snapshot,
        }
    )

    # Reuse the same renderer as the sidebar to keep output behavior consistent.
    render_results(result, params_snapshot)


def render_streaming_tab():
    drain_stream_events(st.session_state)

    sdk_available = streaming_sdk_import() is not None
    if not sdk_available:
        st.warning(
            "Streaming SDK components not available. "
            "Install PyAudio with: `pip install pyaudio`"
        )
        return

    st.subheader("Live Streaming Transcription")
    stream_model_label = st.selectbox("Streaming model", list(STREAMING_MODEL_OPTIONS.keys()))
    stream_model = STREAMING_MODEL_OPTIONS[stream_model_label]
    st.caption("Audio is captured by the local Python process (PyAudio), not by the Chrome tab.")

    if st.session_state.input_devices_cache is None:
        st.session_state.input_devices_cache = list_input_devices()
    input_devices = st.session_state.input_devices_cache
    selected_device_index = st.session_state.stream_device_index
    if input_devices:
        labels = [format_input_device_label(device) for device in input_devices]
        default_pos = 0
        for idx, device in enumerate(input_devices):
            if selected_device_index is not None and device["index"] == selected_device_index:
                default_pos = idx
                break
            if selected_device_index is None and device["is_default"]:
                default_pos = idx
        selected_label = st.selectbox("Input device", labels, index=default_pos)
        selected_device_index = input_devices[labels.index(selected_label)]["index"]
        st.session_state.stream_device_index = selected_device_index
    else:
        st.warning("No input microphone devices were detected by PyAudio.")

    col_start, col_stop = st.columns(2)

    with col_start:
        if st.button("Start", type="primary", disabled=st.session_state.streaming or not input_devices):
            st.session_state.streaming = True
            st.session_state.live_transcript = ""
            st.session_state.stream_session_id = None
            st.session_state.stream_word_count = None
            st.session_state.stream_audio_duration = None
            st.session_state.stream_error = None
            start_streaming_thread(st.session_state, stream_model, API_KEY, selected_device_index)
            st.rerun()

    with col_stop:
        if st.button("Stop", disabled=not st.session_state.streaming):
            stop_streaming(st.session_state)
            st.rerun()

    # Subprocess health indicator
    proc = st.session_state._stream_thread
    if proc is not None:
        pid = st.session_state._stream_proc_pid
        exitcode = st.session_state._stream_proc_exitcode
        alive = hasattr(proc, "is_alive") and proc.is_alive()
        if alive:
            st.caption(f"Process: alive · PID {pid or '...'}")
        elif exitcode is not None:
            if exitcode == 0:
                st.caption(f"Process: exited cleanly (PID {pid}, exit 0)")
            else:
                st.caption(f"Process: crashed (PID {pid}, exit {exitcode})")

    if st.session_state.stream_session_id:
        st.caption(f"Session ID: `{st.session_state.stream_session_id}`")

    if st.session_state.stream_error:
        stream_error = st.session_state.stream_error
        if "pyaudio" in stream_error.lower() or "portaudio" in stream_error.lower():
            st.error(
                f"PyAudio error: {stream_error}\n\n"
                "Install PyAudio: `pip install pyaudio` (may need PortAudio: `brew install portaudio`)"
            )
        elif "input overflowed" in stream_error.lower() or "-9981" in stream_error:
            st.error(
                f"Microphone overflow error: {stream_error}\n\n"
                "Try selecting a different input device and close apps that are actively using the same microphone."
            )
        else:
            st.error(f"Streaming error: {stream_error}")

    st.text_area(
        "Live transcript",
        value=st.session_state.live_transcript or "(waiting for speech...)"
        if st.session_state.streaming
        else st.session_state.live_transcript,
        height=300,
        disabled=True,
    )

    # Live metrics during streaming (must be before rerun)
    if st.session_state.streaming and st.session_state.stream_start_time:
        words_so_far = len(st.session_state.live_transcript.split()) if st.session_state.live_transcript.strip() else 0
        elapsed_min = max((datetime.now() - st.session_state.stream_start_time).total_seconds() / 60, 0.01)
        wpm = round(words_so_far / elapsed_min)
        col_a, col_b = st.columns(2)
        col_a.metric("Words so far", words_so_far)
        col_b.metric("WPM (est.)", wpm)

    if st.session_state.streaming:
        # Streaming callbacks update session state asynchronously; rerun to refresh UI.
        time.sleep(0.5)
        st.rerun()

    if not st.session_state.streaming and st.session_state.stream_audio_duration is not None:
        words = len(st.session_state.live_transcript.split()) if st.session_state.live_transcript.strip() else 0
        elapsed_s = st.session_state.stream_audio_duration
        wpm = round(words / max(elapsed_s / 60, 0.01))
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Word count", words)
        col_b.metric("Audio duration (s)", round(elapsed_s, 1))
        col_c.metric("Avg WPM", wpm)

    # Event log
    if st.session_state.stream_event_log:
        with st.expander(f"Session event log ({len(st.session_state.stream_event_log)} entries)", expanded=False):
            st.text("\n".join(st.session_state.stream_event_log))


def _curl_get(path: str, params: dict | None = None) -> str:
    from .config import API_KEY, BASE_URL
    qs = ("?" + "&".join(f"{k}={v}" for k, v in params.items())) if params else ""
    return f'curl -X GET "{BASE_URL}{path}{qs}" \\\n  -H "Authorization: {API_KEY[:8]}..."'


def _curl_delete(path: str) -> str:
    from .config import API_KEY, BASE_URL
    return f'curl -X DELETE "{BASE_URL}{path}" \\\n  -H "Authorization: {API_KEY[:8]}..."'


def render_debug_tab():
    st.subheader("API Debug / Inspector")

    # ── Health Check ──────────────────────────────────────────────────────────
    st.markdown("### API Health Check")
    st.caption("Validates your API key and measures round-trip latency to the AssemblyAI API.")
    if st.button("Run Health Check", key="debug_health"):
        with st.spinner("Pinging API..."):
            status, ms, rate_headers = check_api_health()
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("HTTP Status", status)
        col_b.metric("Latency (ms)", ms)
        col_c.metric("Auth", "OK" if status < 400 else "FAILED")
        if status == 401:
            st.error("Authentication failed — check your ASSEMBLYAI_API_KEY.")
        elif status < 400:
            st.success("API key is valid and the endpoint is reachable.")
        if rate_headers:
            with st.expander("Rate limit & request headers"):
                st.json(rate_headers)
        with st.expander("Equivalent cURL"):
            st.code(_curl_get("/v2/transcript", {"limit": 1}), language="bash")

    st.divider()

    # ── Transcript Lookup + Deep-Dive ─────────────────────────────────────────
    st.markdown("### Transcript Inspector")
    lookup_id = st.text_input("Transcript ID", key="debug_lookup_id")

    if st.button("Fetch", key="debug_fetch"):
        if not lookup_id.strip():
            st.warning("Enter a transcript ID.")
        else:
            tid = lookup_id.strip()
            with st.spinner("Fetching..."):
                body, status, ms, resp_headers = get_transcript(tid)
            st.caption(f"HTTP {status} · {ms} ms")

            transcript_status = body.get("status")
            transcript_error = body.get("error")
            if transcript_status:
                status_colors = {"completed": "green", "error": "red", "processing": "orange", "queued": "blue"}
                color = status_colors.get(transcript_status, "gray")
                st.markdown(f"**Status:** :{color}[{transcript_status}]")
            if transcript_error:
                st.error(f"Transcript error: {transcript_error}")

            tab_raw, tab_sentences, tab_paragraphs, tab_export, tab_headers = st.tabs(
                ["Raw JSON", "Sentences", "Paragraphs", "Export", "Response Headers"]
            )

            with tab_raw:
                st.json(body)

            with tab_sentences:
                if status < 400 and body.get("status") == "completed":
                    with st.spinner("Fetching sentences..."):
                        sent_body, sent_status, sent_ms = get_transcript_sentences(tid)
                    st.caption(f"HTTP {sent_status} · {sent_ms} ms")
                    sentences = sent_body.get("sentences", [])
                    if sentences:
                        rows = [
                            {
                                "start_ms": s.get("start"),
                                "end_ms": s.get("end"),
                                "duration_ms": (s.get("end", 0) - s.get("start", 0)),
                                "confidence": round(s.get("confidence", 0), 3),
                                "text": s.get("text", ""),
                            }
                            for s in sentences
                        ]
                        st.dataframe(rows, use_container_width=True)
                    else:
                        st.info("No sentences returned.")
                elif body.get("status") != "completed":
                    st.info(f"Transcript status is '{body.get('status')}' — sentences only available when completed.")
                else:
                    st.error(f"Fetch failed (HTTP {status})")

            with tab_paragraphs:
                if status < 400 and body.get("status") == "completed":
                    with st.spinner("Fetching paragraphs..."):
                        para_body, para_status, para_ms = get_transcript_paragraphs(tid)
                    st.caption(f"HTTP {para_status} · {para_ms} ms")
                    paragraphs = para_body.get("paragraphs", [])
                    if paragraphs:
                        for i, p in enumerate(paragraphs, 1):
                            start_s = p.get("start", 0) / 1000
                            end_s = p.get("end", 0) / 1000
                            st.markdown(
                                f"**¶{i}** `{start_s:.1f}s – {end_s:.1f}s` · "
                                f"confidence {round(p.get('confidence', 0), 3)}"
                            )
                            st.write(p.get("text", ""))
                    else:
                        st.info("No paragraphs returned.")
                elif body.get("status") != "completed":
                    st.info(f"Transcript status is '{body.get('status')}' — paragraphs only available when completed.")
                else:
                    st.error(f"Fetch failed (HTTP {status})")

            with tab_export:
                if status < 400 and body.get("status") == "completed":
                    plain_text = body.get("text", "")
                    st.download_button(
                        "Download .txt",
                        data=plain_text,
                        file_name=f"{tid}.txt",
                        mime="text/plain",
                    )
                    st.text_area("Text preview", value=plain_text, height=300, disabled=True)
                elif body.get("status") != "completed":
                    st.info(f"Transcript status is '{body.get('status')}' — export only available when completed.")
                else:
                    st.error(f"Fetch failed (HTTP {status})")

            with tab_headers:
                st.json(resp_headers)

    st.divider()

    # ── Recent Transcripts ────────────────────────────────────────────────────
    st.markdown("### Recent Transcripts")
    limit = st.number_input("Limit", min_value=1, max_value=100, value=10, key="debug_limit")
    if st.button("List", key="debug_list"):
        with st.spinner("Fetching..."):
            body, status, ms = list_transcripts(int(limit))
        st.caption(f"HTTP {status} · {ms} ms")
        transcripts = body.get("transcripts", [])
        if transcripts:
            rows = [
                {
                    "id": transcript.get("id"),
                    "status": transcript.get("status"),
                    "created_at": transcript.get("created"),
                    "audio_duration": transcript.get("audio_duration"),
                }
                for transcript in transcripts
            ]
            st.dataframe(rows, use_container_width=True)
        with st.expander("Raw JSON response"):
            st.json(body)
        with st.expander("Equivalent cURL"):
            st.code(_curl_get("/v2/transcript", {"limit": int(limit)}), language="bash")

    st.divider()

    # ── Delete Transcript ─────────────────────────────────────────────────────
    st.markdown("### Delete Transcript")
    delete_id = st.text_input("Transcript ID to delete", key="debug_delete_id")
    confirm_delete = st.checkbox("I confirm I want to delete this transcript", key="debug_confirm_delete")
    if st.button("Delete", type="primary", key="debug_delete", disabled=not confirm_delete):
        if not delete_id.strip():
            st.warning("Enter a transcript ID.")
        else:
            with st.spinner("Deleting..."):
                body, status, ms = delete_transcript(delete_id.strip())
            st.caption(f"HTTP {status} · {ms} ms")
            if status < 400:
                st.success("Transcript deleted.")
            else:
                st.error(f"Delete failed (HTTP {status})")
            st.json(body)
            with st.expander("Equivalent cURL"):
                st.code(_curl_delete(f"/v2/transcript/{delete_id.strip()}"), language="bash")


def run_app():
    st.set_page_config(page_title="Anub's AAI", page_icon="🍕", layout="wide")
    init_session_state(st.session_state)
    render_sidebar_history()

    st.title("Anub's AssemblyAI Explorer")

    if not API_KEY:
        st.error("ASSEMBLYAI_API_KEY not found. Add it to your .env file.")
        st.stop()

    tab_prerecorded, tab_streaming, tab_debug = st.tabs(["Pre-recorded", "Live Streaming", "API Debug"])
    with tab_prerecorded:
        render_prerecorded_tab()
    with tab_streaming:
        render_streaming_tab()
    with tab_debug:
        render_debug_tab()
