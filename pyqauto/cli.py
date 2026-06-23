from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

import pandas as pd

from astock_source_router.core.models import RouterConfig
from pyqauto import QuoteRouter, __version__

CLI_COMMANDS = {
    "daily",
    "diagnose",
    "full",
    "index",
    "kline",
    "minute",
    "probe-pytdx",
    "realtime",
    "source-schema-probe-live",
}

MINUTE_PERIODS = {"1", "5", "15", "30", "60", "1m", "5m", "15m", "30m", "60m"}
DAILY_PERIODS = {"daily", "day", "1d", "d"}


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def _router(root: Path | None = None, *, auto_register: bool = True) -> QuoteRouter:
    base = root or Path(".")
    return QuoteRouter(
        config=RouterConfig(
            cache_dir=base / ".cache" / "pyqauto_cli",
            log_dir=base / "logs",
            enable_cache=False,
            enable_sqlite_audit=False,
        ),
        auto_register=auto_register,
    )


def _json_output(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "global_json", False) or getattr(args, "json", False))


def _print_payload(payload: Any, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
        return
    print(str(payload))


def _safe_message(exc: Exception) -> str:
    message = str(exc)
    for path in {Path.cwd(), Path(tempfile.gettempdir())}:
        with suppress(OSError):
            resolved = str(path.resolve())
            if resolved:
                message = message.replace(resolved, "<local-path>")
    return message


def _print_error(exc: Exception, *, json_output: bool) -> None:
    payload = {
        "status": "ERROR",
        "error_type": type(exc).__name__,
        "message": _safe_message(exc),
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str), file=sys.stderr)
        return
    print(f"{payload['error_type']}: {payload['message']}", file=sys.stderr)


def _print_frame(frame: pd.DataFrame, *, json_output: bool, count: int | None = None) -> None:
    output = frame.head(count).copy() if count is not None else frame
    if json_output:
        print(json.dumps(output.to_dict(orient="records"), ensure_ascii=False, indent=2, default=str))
        return
    if output.empty:
        print("rows: 0")
        return
    print(output.to_string(index=False))


def _run_frame_command(
    args: argparse.Namespace,
    fetch: Callable[[QuoteRouter], pd.DataFrame],
    *,
    count: int | None = None,
) -> int:
    try:
        frame = fetch(_router(auto_register=True))
    except Exception as exc:
        _print_error(exc, json_output=_json_output(args))
        return 1
    _print_frame(frame, json_output=_json_output(args), count=count)
    return 0


def _require_pytdx_for_minute_kline() -> None:
    if importlib.util.find_spec("pytdx") is None:
        raise RuntimeError(
            "pytdx is required for pyqauto minute K-line support. "
            "Install pyqauto normally or install pytdx>=1.72."
        )


def _diagnose(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="pyqauto_cli_") as tmp:
        payload = _router(Path(tmp), auto_register=False).diagnose()
    _print_payload(payload, json_output=_json_output(args))
    return 0


def _source_schema_probe_live(args: argparse.Namespace) -> int:
    if os.environ.get("ENABLE_LIVE_SMOKE_TEST") != "1":
        payload = {
            "status": "SKIPPED",
            "reason": "live probe requires ENABLE_LIVE_SMOKE_TEST=1",
            "network_used": False,
        }
        _print_payload(payload, json_output=_json_output(args))
        return 0
    payload = {
        "status": "UNAVAILABLE",
        "reason": "live source schema probe is not wired in this release candidate build",
        "network_used": False,
    }
    _print_payload(payload, json_output=_json_output(args))
    return 1


def _probe_pytdx(args: argparse.Namespace) -> int:
    if os.environ.get("ENABLE_LIVE_SMOKE_TEST") != "1":
        payload = {
            "status": "SKIPPED",
            "reason": "pytdx probe requires ENABLE_LIVE_SMOKE_TEST=1",
            "network_used": False,
        }
        _print_payload(payload, json_output=_json_output(args))
        return 0
    payload = {
        "status": "UNAVAILABLE",
        "reason": "pytdx live probe is not wired in this release candidate build",
        "network_used": False,
    }
    _print_payload(payload, json_output=_json_output(args))
    return 1


def _realtime(args: argparse.Namespace) -> int:
    return _run_frame_command(args, lambda router: router.realtime_quotes(list(args.symbols)))


def _full(args: argparse.Namespace) -> int:
    return _run_frame_command(args, lambda router: router.full_realtime_quotes(list(args.symbols)))


def _index(args: argparse.Namespace) -> int:
    return _run_frame_command(args, lambda router: router.index_realtime(list(args.symbols)))


def _minute(args: argparse.Namespace) -> int:
    def fetch(router: QuoteRouter) -> pd.DataFrame:
        _require_pytdx_for_minute_kline()
        return router.minute_kline(args.symbol, period=str(args.period).lower().rstrip("m"), adjust=args.adjust)

    return _run_frame_command(args, fetch, count=args.count)


def _daily(args: argparse.Namespace) -> int:
    def fetch(router: QuoteRouter) -> pd.DataFrame:
        if args.start_date is None or args.end_date is None:
            raise ValueError("daily requires --start-date and --end-date")
        return router.daily_kline(
            args.symbol,
            start_date=args.start_date,
            end_date=args.end_date,
            adjust=args.adjust,
        )

    return _run_frame_command(args, fetch, count=args.count)


def _kline(args: argparse.Namespace) -> int:
    def fetch(router: QuoteRouter) -> pd.DataFrame:
        period = str(args.period).lower()
        if period in MINUTE_PERIODS:
            _require_pytdx_for_minute_kline()
            return router.kline(args.symbol, period=period, adjust=args.adjust)
        if period in DAILY_PERIODS:
            return router.kline(
                args.symbol,
                start_date=args.start_date,
                end_date=args.end_date,
                period=period,
                adjust=args.adjust,
            )
        raise ValueError(f"unsupported kline period: {args.period}")

    return _run_frame_command(args, fetch, count=args.count)


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Print JSON output where supported.")


def _add_adjust(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--adjust", default="", help="Adjustment flag passed through to the router.")


def _add_date_range(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-date", default=None, help="Start date for daily K-line periods.")
    parser.add_argument("--end-date", default=None, help="End date for daily K-line periods.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyqauto", description="pyqauto local quote router")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", dest="global_json", action="store_true", help="Print JSON output where supported.")
    subparsers = parser.add_subparsers(dest="command")

    realtime = subparsers.add_parser("realtime", help="Fetch realtime quotes.")
    realtime.add_argument("symbols", nargs="+", help="Stock symbols.")
    _add_json(realtime)
    realtime.set_defaults(func=_realtime)

    full = subparsers.add_parser("full", help="Fetch full realtime quotes.")
    full.add_argument("symbols", nargs="+", help="Stock symbols.")
    _add_json(full)
    full.set_defaults(func=_full)

    index = subparsers.add_parser("index", help="Fetch index realtime quotes.")
    index.add_argument("symbols", nargs="*", help="Index symbols.")
    _add_json(index)
    index.set_defaults(func=_index)

    minute = subparsers.add_parser("minute", help="Fetch pytdx-only minute K-line records.")
    minute.add_argument("symbol", help="Stock symbol.")
    minute.add_argument("--period", default="5m", help="Minute period: 1m, 5m, 15m, 30m, or 60m.")
    minute.add_argument("--count", default=120, type=_positive_int, help="Maximum rows to print.")
    _add_adjust(minute)
    _add_json(minute)
    minute.set_defaults(func=_minute)

    daily = subparsers.add_parser("daily", help="Fetch daily K-line records.")
    daily.add_argument("symbol", help="Stock symbol.")
    daily.add_argument("--count", default=120, type=_positive_int, help="Maximum rows to print.")
    _add_date_range(daily)
    _add_adjust(daily)
    _add_json(daily)
    daily.set_defaults(func=_daily)

    kline = subparsers.add_parser("kline", help="Fetch K-line records through the frozen API.")
    kline.add_argument("symbol", nargs="?", help="Stock symbol.")
    kline.add_argument("--period", default="5m", help="K-line period.")
    kline.add_argument("--count", default=120, type=_positive_int, help="Maximum rows to print.")
    _add_date_range(kline)
    _add_adjust(kline)
    _add_json(kline)
    kline.set_defaults(func=_kline)

    diagnose = subparsers.add_parser("diagnose", help="Show local router diagnostics.")
    _add_json(diagnose)
    diagnose.set_defaults(func=_diagnose)

    source_probe = subparsers.add_parser(
        "source-schema-probe-live",
        help="Inspect live source schema drift when explicitly enabled.",
    )
    _add_json(source_probe)
    source_probe.set_defaults(func=_source_schema_probe_live)

    pytdx_probe = subparsers.add_parser(
        "probe-pytdx",
        help="Probe pytdx servers when explicitly enabled.",
    )
    _add_json(pytdx_probe)
    pytdx_probe.set_defaults(func=_probe_pytdx)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    if getattr(args, "command", None) == "kline" and not getattr(args, "symbol", None):
        parser.error("kline requires SYMBOL unless only --help is requested")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
