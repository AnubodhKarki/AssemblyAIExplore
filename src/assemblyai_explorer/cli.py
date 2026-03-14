import sys
from pathlib import Path

from streamlit.web import cli as stcli


def main():
    app_path = Path(__file__).with_name("streamlit_app.py")
    sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
    raise SystemExit(stcli.main())
