from pathlib import Path

# Project
PROJ_ROOT = Path(__file__).resolve().parent.parent

# DB
DB_PATH = str(PROJ_ROOT / "data" / "moonfish.db")
