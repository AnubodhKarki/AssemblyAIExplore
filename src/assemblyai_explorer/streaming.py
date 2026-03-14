import multiprocessing
import os
import queue
from datetime import datetime


def streaming_sdk_import():
    try:
        import assemblyai as aai
        from assemblyai.streaming.v3 import (
            BeginEvent,
            StreamingClient,
            StreamingClientOptions,
            StreamingEvents,
            StreamingParameters,
            TerminationEvent,
            TurnEvent,
        )
    except ImportError:
        return None

    return {
        "aai": aai,
        "BeginEvent": BeginEvent,
        "TurnEvent": TurnEvent,
        "TerminationEvent": TerminationEvent,
        "StreamingClient": StreamingClient,
        "StreamingClientOptions": StreamingClientOptions,
        "StreamingParameters": StreamingParameters,
        "StreamingEvents": StreamingEvents,
    }


def format_input_device_label(device: dict) -> str:
    return f"[{device['index']}] {device['name']} ({int(device['default_sample_rate'])} Hz)"


def list_input_devices() -> list[dict]:
    try:
        import pyaudio
    except ImportError:
        return []

    devices = []
    audio = pyaudio.PyAudio()
    try:
        default_info = audio.get_default_input_device_info()
        default_index = int(default_info.get("index"))
    except Exception:
        default_index = None

    try:
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            max_input_channels = int(info.get("maxInputChannels", 0) or 0)
            if max_input_channels > 0:
                devices.append(
                    {
                        "index": int(info["index"]),
                        "name": str(info.get("name", f"Device {i}")),
                        "default_sample_rate": float(info.get("defaultSampleRate", 16000.0)),
                        "is_default": int(info["index"]) == default_index,
                    }
                )
    finally:
        audio.terminate()

    return devices


def _emit(events_queue, event_type: str, payload=None):
    events_queue.put((event_type, payload))


def _log(events_queue, message: str):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    events_queue.put(("log", f"[{ts}] {message}"))


def is_input_overflow_error(exc: BaseException) -> bool:
    if not isinstance(exc, OSError):
        return False
    if getattr(exc, "errno", None) == -9981:
        return True
    return "input overflowed" in str(exc).lower()


class PyAudioMicrophoneStream:
    def __init__(self, sample_rate: int = 16000, device_index: int | None = None, stop_event=None):
        try:
            import pyaudio
        except ImportError as exc:
            raise ImportError("PyAudio is required for local microphone streaming.") from exc

        self._pyaudio = pyaudio.PyAudio()
        self.sample_rate = sample_rate
        self._chunk_size = int(self.sample_rate * 0.1)
        self._silence_frame = b"\x00" * (self._chunk_size * 2)
        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=self._chunk_size,
            input_device_index=device_index,
        )
        self._open = True
        self._stop_event = stop_event

    def __iter__(self):
        return self

    def __next__(self):
        if not self._open or (self._stop_event is not None and self._stop_event.is_set()):
            raise StopIteration
        try:
            return self._stream.read(self._chunk_size, exception_on_overflow=False)
        except TypeError:
            # Fallback for uncommon PyAudio builds that do not expose the keyword argument.
            try:
                return self._stream.read(self._chunk_size)
            except OSError as exc:
                if is_input_overflow_error(exc):
                    return self._silence_frame
                raise
        except OSError as exc:
            if is_input_overflow_error(exc):
                return self._silence_frame
            raise

    def close(self):
        self._open = False
        if self._stream.is_active():
            self._stream.stop_stream()
        self._stream.close()
        self._pyaudio.terminate()


def build_streaming_parameters(StreamingParameters, aai, model: str):
    params = {
        "sample_rate": 16000,
        "encoding": aai.AudioEncoding.pcm_s16le,
        "format_turns": True,
    }
    if "speech_model" in StreamingParameters.model_fields:
        params["speech_model"] = model
    elif "model" in StreamingParameters.model_fields:
        params["model"] = model
    else:
        raise ValueError("StreamingParameters does not support 'speech_model' or 'model'.")
    return StreamingParameters(**params)


def run_streaming_session(events_queue, model: str, api_key: str, device_index: int | None, stop_event=None):
    _log(events_queue, f"Process started (PID {os.getpid()}), model={model}")
    _emit(events_queue, "pid", os.getpid())

    sdk = streaming_sdk_import()
    if sdk is None:
        _emit(events_queue, "error", "Streaming SDK not available.")
        _emit(events_queue, "stream_ended", None)
        return

    aai = sdk["aai"]
    StreamingClient = sdk["StreamingClient"]
    StreamingClientOptions = sdk["StreamingClientOptions"]
    StreamingParameters = sdk["StreamingParameters"]
    StreamingEvents = sdk["StreamingEvents"]

    turn_count = 0
    mic = None
    client = None
    try:
        aai.settings.api_key = api_key

        def on_begin(_client, event):
            _emit(events_queue, "session_id", event.id)
            _log(events_queue, f"Session began: {event.id}")

        def on_turn(_client, event):
            nonlocal turn_count
            transcript = (event.transcript or "").strip()
            if not transcript:
                return
            if event.turn_is_formatted or event.end_of_turn:
                turn_count += 1
                _emit(events_queue, "transcript_line", transcript)
                _log(events_queue, f"Turn {turn_count} received ({len(transcript.split())} words)")

        def on_termination(_client, event):
            _log(events_queue, f"Termination event: audio_duration={event.audio_duration_seconds:.1f}s, turns={turn_count}")
            _emit(events_queue, "audio_duration", event.audio_duration_seconds)
            _emit(events_queue, "stream_ended", None)

        _log(events_queue, f"Opening microphone (device_index={device_index})")
        mic = PyAudioMicrophoneStream(sample_rate=16000, device_index=device_index, stop_event=stop_event)
        _log(events_queue, "Microphone opened. Connecting to streaming.assemblyai.com...")

        client = StreamingClient(
            StreamingClientOptions(
                api_key=api_key,
                api_host="streaming.assemblyai.com",
            )
        )

        client.on(StreamingEvents.Begin, on_begin)
        client.on(StreamingEvents.Turn, on_turn)
        client.on(StreamingEvents.Termination, on_termination)

        client.connect(build_streaming_parameters(StreamingParameters, aai, model))
        _log(events_queue, "WebSocket connected. Streaming audio...")
        client.stream(mic)
    except Exception as exc:
        _log(events_queue, f"Exception: {exc}")
        _emit(events_queue, "error", str(exc))
    finally:
        _log(events_queue, "Cleaning up client and microphone...")
        if client is not None:
            try:
                client.disconnect(terminate=True)
            except Exception:
                pass
        if mic is not None:
            try:
                mic.close()
            except OSError as exc:
                _emit(events_queue, "error", str(exc))
        _log(events_queue, "Session ended.")
        _emit(events_queue, "stream_ended", None)


def start_streaming_thread(session_state, model: str, api_key: str, device_index: int | None):
    # Run in a separate process so a PyAudio segfault can't kill Streamlit.
    # multiprocessing.Queue works across process boundaries; queue.Queue does not.
    events_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()
    session_state._stream_events = events_queue
    session_state._stream_stop_event = stop_event
    session_state.stream_event_log = []
    session_state.stream_start_time = datetime.now()
    session_state._stream_proc_pid = None
    session_state._stream_proc_exitcode = None
    proc = multiprocessing.Process(
        target=run_streaming_session,
        args=(events_queue, model, api_key, device_index, stop_event),
        daemon=True,
    )
    session_state._stream_thread = proc
    proc.start()


def drain_stream_events(session_state):
    events_queue = session_state._stream_events
    if events_queue is None:
        return

    # Track child process health.
    proc = session_state._stream_thread
    if proc is not None and hasattr(proc, "exitcode") and proc.exitcode is not None:
        session_state._stream_proc_exitcode = proc.exitcode

    proc_crashed = (
        proc is not None
        and hasattr(proc, "exitcode")
        and proc.exitcode is not None
        and proc.exitcode != 0
    )

    while True:
        try:
            event_type, payload = events_queue.get_nowait()
        except queue.Empty:
            break

        if event_type == "session_id":
            session_state.stream_session_id = payload
        elif event_type == "transcript_line":
            session_state.live_transcript += payload + "\n"
        elif event_type == "audio_duration":
            session_state.stream_word_count = payload
            session_state.stream_audio_duration = payload
        elif event_type == "error":
            session_state.stream_error = payload
            session_state.stream_event_log.append(f"ERROR: {payload}")
        elif event_type == "log":
            session_state.stream_event_log.append(payload)
        elif event_type == "pid":
            session_state._stream_proc_pid = payload
        elif event_type == "stream_ended":
            session_state.streaming = False

    if proc_crashed and session_state.streaming:
        session_state.streaming = False
        session_state.stream_error = "Streaming process crashed (segfault or fatal error). Other features are unaffected."


def stop_streaming(session_state):
    # Signal the child process to stop gracefully via the shared event.
    stop_event = getattr(session_state, "_stream_stop_event", None)
    if stop_event is not None:
        stop_event.set()

    # Force-kill the child process if it's still alive after signalling.
    proc = session_state._stream_thread
    if proc is not None and hasattr(proc, "is_alive") and proc.is_alive():
        proc.join(timeout=3)
        if proc.is_alive():
            proc.terminate()

    session_state._stream_client = None
    session_state._stream_microphone = None
    session_state.streaming = False
