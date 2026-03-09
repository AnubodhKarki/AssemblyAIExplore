# AssemblyAI API Exploration

Notebook I put together while learning the AssemblyAI REST API. Covers the full transcription lifecycle and a few extras like LeMUR Q&A (paid plan, could integrate OpenAI, Claude or Gemini API to process the transcript separtely).

## What's in here

`notebooks/assemblyai_api_checks.ipynb` - walks through the main REST API operations in order:

- Submit a transcription job
- Check status / poll to completion
- Fetch transcript text + word-level timestamps
- List and delete past transcripts
- Upload a local audio file
- Ask questions with LeMUR

## Setup

```bash
git clone https://github.com/AnubodhKarki/assembly_ai.git
cd assembly_ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add your key to .env
```

Then open the notebook:

```bash
jupyter notebook notebooks/assemblyai_api_checks.ipynb
```

Run Cell 1 first - it loads the API key and sets up the shared variables everything else depends on.

## Notes
- Audio redirects do not work
- LeMUR needs a paid plan, the cell handles the 401 gracefully
- The delete cell has an intentional assert so you can't run it by accident
