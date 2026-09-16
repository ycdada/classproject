import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_test_db_dir = Path(__file__).resolve().parents[1] / "data"
_test_db_dir.mkdir(exist_ok=True)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")

