"""Arranque directo desde la raíz del proyecto (delega en backend/run.py).
Uso: python run.py
"""
import runpy
import sys
from pathlib import Path

BACKEND_RUN = Path(__file__).resolve().parent / "backend" / "run.py"
sys.path.insert(0, str(BACKEND_RUN.parent))
runpy.run_path(str(BACKEND_RUN), run_name="__main__")

