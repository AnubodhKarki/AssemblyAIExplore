from pathlib import Path
import sys

# Allow `streamlit run src/assemblyai_explorer/streamlit_app.py` without installation.
SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from assemblyai_explorer.ui import run_app


run_app()
