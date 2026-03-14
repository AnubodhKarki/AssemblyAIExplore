def init_session_state(session_state):
    if "history" not in session_state:
        session_state.history = []

    for key, default in [
        ("streaming", False),
        ("input_devices_cache", None),
        ("live_transcript", ""),
        ("stream_session_id", None),
        ("stream_word_count", None),
        ("stream_audio_duration", None),
        ("stream_error", None),
        ("stream_device_index", None),
        ("_stream_thread", None),
        ("_stream_client", None),
        ("_stream_microphone", None),
        ("_stream_events", None),
        ("_stream_stop_event", None),
        ("stream_event_log", []),
        ("stream_start_time", None),
        ("_stream_proc_pid", None),
        ("_stream_proc_exitcode", None),
    ]:
        if key not in session_state:
            session_state[key] = default
