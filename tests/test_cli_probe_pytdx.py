from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "aquote_router.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def test_probe_pytdx_help_can_run() -> None:
    result = run_cli("probe-pytdx", "--help")

    assert result.returncode == 0, result.stderr
    assert "--config" in result.stdout
    assert "--output" in result.stdout
    assert "--timeout" in result.stdout
    assert "--limit" in result.stdout


def test_kline_help_allows_command_level_pytdx_servers_override() -> None:
    result = run_cli("kline", "--help")

    assert result.returncode == 0, result.stderr
    assert "--pytdx-servers" in result.stdout
