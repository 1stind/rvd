"""The README documents a SQLite dev setup; the engine must at least build with it."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_database_module_imports_with_sqlite_url():
    env = {**os.environ, "DATABASE_URL": "sqlite+aiosqlite:///:memory:", "PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.database"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr[-600:]
