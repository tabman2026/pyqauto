from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from astock_source_router.core.models import RouterConfig
from pyqauto import QuoteRouter


def _router(root: Path | None = None) -> QuoteRouter:
    base = root or Path(".")
    return QuoteRouter(
        config=RouterConfig(
            cache_dir=base / ".cache" / "pyqauto_cli",
            log_dir=base / "logs",
            enable_cache=False,
            enable_sqlite_audit=False,
        ),
        auto_register=False,
    )


def _print_payload(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _diagnose(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="pyqauto_cli_") as tmp:
        payload = _router(Path(tmp)).diagnose()
    _print_payload(payload, json_output=bool(args.json))
    return 0


def _source_schema_probe_live(args: argparse.Namespace) -> int:
    if os.environ.get("ENABLE_LIVE_SMOKE_TEST") != "1":
        payload = {
            "status": "SKIPPED",
            "reason": "live probe requires ENABLE_LIVE_SMOKE_TEST=1",
            "network_used": False,
        }
        _print_payload(payload, json_output=bool(args.json))
        return 0
    payload = {
        "status": "UNAVAILABLE",
        "reason": "live source schema probe is not wired in this release candidate build",
        "network_used": False,
    }
    _print_payload(payload, json_output=bool(args.json))
    return 1


def _probe_pytdx(args: argparse.Namespace) -> int:
    if os.environ.get("ENABLE_LIVE_SMOKE_TEST") != "1":
        payload = {
            "status": "SKIPPED",
            "reason": "pytdx probe requires ENABLE_LIVE_SMOKE_TEST=1",
            "network_used": False,
        }
        _print_payload(payload, json_output=bool(args.json))
        return 0
    payload = {
        "status": "UNAVAILABLE",
        "reason": "pytdx live probe is not wired in this release candidate build",
        "network_used": False,
    }
    _print_payload(payload, json_output=bool(args.json))
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyqauto", description="pyqauto local quote router")
    parser.add_argument("--json", action="store_true", help="Print JSON output where supported.")
    subparsers = parser.add_subparsers(dest="command")

    diagnose = subparsers.add_parser("diagnose", help="Show local router diagnostics.")
    diagnose.add_argument("--json", action="store_true", help="Print JSON diagnostics.")
    diagnose.set_defaults(func=_diagnose)

    source_probe = subparsers.add_parser(
        "source-schema-probe-live",
        help="Inspect live source schema drift when explicitly enabled.",
    )
    source_probe.add_argument("--json", action="store_true", help="Print JSON probe status.")
    source_probe.set_defaults(func=_source_schema_probe_live)

    pytdx_probe = subparsers.add_parser(
        "probe-pytdx",
        help="Probe pytdx servers when explicitly enabled.",
    )
    pytdx_probe.add_argument("--json", action="store_true", help="Print JSON probe status.")
    pytdx_probe.set_defaults(func=_probe_pytdx)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
