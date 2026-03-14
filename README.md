# AssemblyAI Explorer

A hands-on support engineering toolkit built to deeply understand every AssemblyAI API feature and to have a reproducible debugging environment for customer integrations.

The project has two surfaces: a Jupyter notebook for raw API exploration, and a Streamlit app that mirrors the kind of tooling a support engineer uses when working through a live customer issue.

---

## Why this exists

Support work lives at the intersection of customer context and API behaviour. To do it well you need to be able to:

- **Reproduce the customer's exact request** and see the raw response.
- **Inspect a transcript at every level**, status, error message, sentences, paragraphs, word timestamps.
- **Validate API connectivity and auth** quickly before escalating to engineering.
- **Show a customer exactly what to send**, not just describe it.
- **Debug streaming failures** without letting one crash take down everything else.

Each section of this app was built with one of those needs in mind.

---

## Customer scenarios

### "My transcription came back with an error"

Open the **API Debug → Transcript Inspector** tab. Enter the transcript ID. The status badge shows the current state (`completed`, `error`, `processing`, `queued`) and any `error` field from the API surfaces immediately in red, no need to parse raw JSON. From the same view you can open the Sentences tab to check word-level confidence scores, which can point to audio quality issues.

### "I'm not getting a response from the API at all"

Run **API Health Check** (one click). It validates the API key, measures round-trip latency, and surfaces rate-limit headers and the `X-Request-Id`. If auth fails it says so directly. This also gives you the `X-Request-Id` to pass to engineering for log lookup.

### "How do I extract just the text from a transcript?"

From the **Export tab** in the Transcript Inspector you can preview and download the plain transcript text directly. Alongside that you can show the customer the cURL command that fetches it, every action in the debug tab generates the equivalent `curl` call so customers can reproduce it immediately in their own terminal without needing an SDK.

### "Our live streaming integration keeps crashing the whole app"

The streaming tab shows a **subprocess health indicator** with PID and exit code. When PyAudio triggers a segmentation fault (exit code `-11`), it kills the child process but the Streamlit app keeps running, isolated at the OS process level, not just a thread. The **session event log** records every internal event with millisecond timestamps (mic open, WebSocket connected, each turn received with word count, errors, disconnect) so there's a full paper trail to attach to a bug report.

### "What's the fastest way to reproduce a customer's exact request?"

The **Pre-recorded tab** surfaces every API parameter (model, language, speaker labels, sentiment, entities, topics, keyterms, context prompt) as UI controls. Submit a transcription and the exact JSON payload is shown inline before the request is sent, and the raw JSON response is available afterwards, this is the request the customer sent, with nothing hidden.

---

## App: Streamlit Explorer

```bash
poetry install
cp .env.example .env
# add ASSEMBLYAI_API_KEY to .env
poetry run explorer
```

To enable the **Live Streaming** tab locally, install the optional live-audio dependency:

```bash
poetry install --extras live
```

### Tabs

**Pre-recorded**
- Audio source: default sample URL, custom URL, or file upload
- Full model and language selection
- Every feature flag exposed: speaker labels, sentiment analysis, entity detection, key phrases, topic detection (IAB), filter profanity, punctuation, format text, disfluencies
- Advanced: expected speaker count, keyterms, context prompt
- Request payload shown inline before submission; raw JSON response available after

**Live Streaming**
- Streaming model selection (Universal-3 Pro, multilingual, Whisper)
- Local microphone input via PyAudio with device selection
- Live transcript display with 0.5s refresh
- Live word count and estimated WPM during session
- Post-session metrics: total words, audio duration, average WPM
- Session event log with millisecond timestamps for every lifecycle event
- Subprocess health: PID, alive/exited/crashed status, exit code
- Subprocess isolation: PyAudio segfaults kill only the child process, not Streamlit

**API Debug**
- **Health Check**: API key validation, round-trip latency, rate-limit headers, `X-Request-Id`
- **Transcript Inspector**: status badge, error surface, five sub-tabs:
  - Raw JSON
  - Sentences, table with `start_ms`, `end_ms`, `duration_ms`, confidence, text
  - Paragraphs, rendered with timestamps and confidence per block
  - Export, plain text preview and `.txt` download
  - Response Headers
- **Recent Transcripts**: paginated list with status, created timestamp, audio duration
- **Delete Transcript**: with confirmation gate
- **cURL generator**: every action shows the equivalent `curl` command with auth header

---

## Notebook: API Exploration

`notebooks/assemblyai_api_checks.ipynb` walks the full transcription lifecycle against the live API:

- Submit a transcription job
- Poll to completion and handle intermediate states
- Fetch transcript text and word-level timestamps
- List and delete past transcripts
- Upload a local audio file (the upload endpoint returns a CDN URL)
- LeMUR Q&A (requires paid plan; cell handles the 401 gracefully and notes that the transcript can be passed to any LLM API instead)

Run Cell 1 first, it loads the API key and initialises the shared `transcript_id` variable that downstream cells depend on.

```bash
jupyter notebook notebooks/assemblyai_api_checks.ipynb
```

---

## Project structure

```
src/assemblyai_explorer/
├── config.py       env + constants, auth header helper
├── api.py          all REST calls, returns (json, status, latency) tuples
├── payloads.py     pure payload builders, no Streamlit dependency
├── rendering.py    transcript output rendering, IAB score normalisation
├── state.py        session state defaults in one place
├── streaming.py    streaming lifecycle, subprocess isolation, event log
└── ui.py           tab composition, orchestrates all modules
```

See `DEVELOPER_GUIDE.md` for architecture walkthrough, data flow diagrams, and a step-by-step guide to adding new features safely.

---

## Tests

```bash
poetry run pytest -q
```

Tests cover payload composition rules, edge cases, and rendering helpers, the pure logic that doesn't require a live API key or a browser.

---

## Notes

- Audio redirect URLs (302) do not work with the AssemblyAI upload endpoint, use a direct file URL or the file upload path.
- LeMUR requires a paid plan. The notebook cell handles the 401 gracefully.
- Live streaming requires PyAudio + PortAudio. On macOS: `brew install portaudio` then `pip install pyaudio`.
- Streamlit Community Cloud does not reliably support building/running PyAudio. Deploy cloud usage for Pre-recorded/API Debug; use local runs for Live Streaming.
- The delete cell in the notebook has an intentional `assert` guard so it cannot be run accidentally.
