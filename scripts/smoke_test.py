"""Offline smoke test for aquote-router."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aquote_router.policy import load_pytdx_servers, load_source_policy


def main() -> int:
    policy = load_source_policy(ROOT / "config" / "source_policy.example.yaml")
    servers = load_pytdx_servers(ROOT / "config" / "pytdx_servers.example.json")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    cli_result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "aquote_router.cli", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    if cli_result.returncode != 0:
        print(cli_result.stderr)
        return cli_result.returncode

    summary = {
        "policy_apis": sorted(policy.apis),
        "pytdx_server_count": len(servers),
        "cli_help_ok": True,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
