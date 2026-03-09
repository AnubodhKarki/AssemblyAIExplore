# assemblyai_api_checks.ipynb

Notebook covering the main AssemblyAI REST API operations. Run Cell 1 first - everything else depends on the variables it sets.

## Cells

1. **Setup** - imports, load API key from `.env`, set `BASE_URL` and `HEADERS`
2. **Submit job** - POST to `/v2/transcript`, stores `TRANSCRIPT_ID`
3. **Check status** - single GET to see where a job is at
4. **Poll to completion** - loop + sleep until `status == "completed"`
5. **Full transcript** - fetch text + language/duration/confidence
6. **Word timestamps** - per-word `start`, `end`, `confidence` (ms)
7. **List transcripts** - recent jobs with `?limit=N`
8. **Delete** - HTTP DELETE with an assert guard so you can't run it accidentally
9. **Upload local file** - stream bytes to `/v2/upload`, get back a hosted URL
10. **LeMUR Q&A** - ask a question about a transcript (needs paid plan)
11. **Raw inspector** - `pprint` the full JSON for any transcript ID

## Common issues

- `400` on submit → audio URL probably redirects; use the final direct URL
- `NameError: TRANSCRIPT_ID` → run Cell 2 first
- `401` on LeMUR → free plan; upgrade at assemblyai.com/pricing
