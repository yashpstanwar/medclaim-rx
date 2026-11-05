"""MedClaim Rx — Streamlit Entrypoint Root Wrapper.

Provides an entrypoint at repository root for Streamlit Community Cloud deployments
that look for 'streamlit_app.py'.
"""

import sys
from pathlib import Path
import runpy

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Execute app/ui.py
runpy.run_path(str(ROOT_DIR / "app" / "ui.py"), run_name="__main__")
