from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_excludes_local_active_pool_and_logs() -> None:
    lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "config/pytdx_servers.active.local.json" in lines
    assert "logs/" in lines
    assert "*.sqlite3" in lines
    assert "*.jsonl" in lines
