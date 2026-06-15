from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_excludes_active_local_pool_and_logs() -> None:
    text = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "exclude config/pytdx_servers.active.local.json" in text
    assert "prune logs" in text
    assert "global-exclude *.sqlite3" in text
    assert "global-exclude *.jsonl" in text
