"""Command line interface for pyqauto."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from pyqauto import __version__
from pyqauto.diagnostics import build_diagnostics
from pyqauto.exceptions import QuoteRouterError
from pyqauto.policy import DEFAULT_PYTDX_SERVERS_PATH, DEFAULT_SOURCE_POLICY_PATH
from pyqauto.pytdx_probe import (
    DEFAULT_CONFIG as DEFAULT_PROBE_CONFIG,
)
from pyqauto.pytdx_probe import (
    DEFAULT_OUTPUT as DEFAULT_PROBE_OUTPUT,
)
from pyqauto.pytdx_probe import (
    run_probe,
)
from pyqauto.router import QuoteRouter
from pyqauto.source_schema_live import (
    LIVE_PROBE_LOG_PATH,
    LIVE_PROBE_REPORT_PATH,
    run_source_schema_probe_live,
)

DEFAULT_PYTDX_SERVERS = DEFAULT_PYTDX_SERVERS_PATH
DEFAULT_SOURCE_POLICY = DEFAULT_SOURCE_POLICY_PATH


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
@click.option("--config", "source_policy_path", default=DEFAULT_SOURCE_POLICY, show_default=True)
@click.option("--pytdx-servers", default=DEFAULT_PYTDX_SERVERS, show_default=True)
@click.option("--audit-jsonl", default=None)
@click.option("--audit-sqlite", default=None)
@click.option("--json", "json_output", is_flag=True)
@click.pass_context
def main(
    ctx: click.Context,
    source_policy_path: str,
    pytdx_servers: str,
    audit_jsonl: str | None,
    audit_sqlite: str | None,
    json_output: bool,
) -> None:
    """A-share quote source router."""

    ctx.obj = {
        "source_policy_path": source_policy_path,
        "pytdx_servers_path": pytdx_servers,
        "audit_jsonl_path": audit_jsonl,
        "audit_sqlite_path": audit_sqlite,
        "json_output": json_output,
    }


@main.command()
@click.option("--json", "diagnose_json_output", is_flag=True)
@click.pass_obj
def diagnose(options: dict[str, Any], diagnose_json_output: bool) -> None:
    """Show local configuration summary without provider connections."""

    payload = build_diagnostics(
        source_policy_path=options["source_policy_path"],
        pytdx_servers_path=options["pytdx_servers_path"],
        audit_jsonl_path=options["audit_jsonl_path"],
        audit_sqlite_path=options["audit_sqlite_path"],
    )
    _print_payload(
        payload,
        json_output=bool(options["json_output"] or diagnose_json_output),
    )


@main.command("probe-pytdx")
@click.option("--config", "config_path", default=DEFAULT_PROBE_CONFIG, show_default=True)
@click.option("--output", "output_path", default=DEFAULT_PROBE_OUTPUT, show_default=True)
@click.option("--json", "probe_json_output", is_flag=True)
@click.option("--timeout", default=3.0, show_default=True, type=float)
@click.option(
    "--limit",
    default=0,
    show_default=True,
    type=int,
    help="Limit probed candidates after loading and de-duplicating; 0 means no limit.",
)
@click.option("--symbol", default="000001", show_default=True)
@click.option(
    "--minute-period",
    default="15m",
    show_default=True,
    type=click.Choice(["1m", "5m", "15m", "30m", "60m"]),
)
@click.option("--count", default=10, show_default=True, type=int)
@click.option("--workers", default=8, show_default=True, type=int)
def probe_pytdx(
    config_path: str,
    output_path: str,
    probe_json_output: bool,
    timeout: float,
    limit: int,
    symbol: str,
    minute_period: str,
    count: int,
    workers: int,
) -> None:
    """Probe pytdx server availability and write a local active pool."""

    try:
        payload = run_probe(
            config_path=config_path,
            output_path=output_path,
            timeout=timeout,
            limit=limit,
            symbol=symbol,
            minute_period=minute_period,
            count=count,
            workers=workers,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    if probe_json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(
        "Pytdx probe finished: "
        f"{payload['connect_success_count']}/{payload['probe_server_count']} "
        "servers connected. "
        f"Active config: {payload['active_config_path']}"
    )


@main.command(
    "source-schema-probe-live",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option("--json", "probe_json_output", is_flag=True)
@click.option("--output", "output_path", default=str(LIVE_PROBE_REPORT_PATH), show_default=True)
@click.option("--jsonl", "jsonl_path", default=str(LIVE_PROBE_LOG_PATH), show_default=True)
@click.option("--pytdx-servers", "command_pytdx_servers", default=None)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def source_schema_probe_live(
    ctx: click.Context,
    probe_json_output: bool,
    output_path: str,
    jsonl_path: str,
    command_pytdx_servers: str | None,
    extra_args: tuple[str, ...],
) -> None:
    """Run live source schema drift checks; supports --symbols CODE CODE."""

    options = ctx.obj or {}
    symbols = _parse_live_probe_symbols(extra_args)
    payload = run_source_schema_probe_live(
        report_path=output_path,
        log_path=jsonl_path,
        pytdx_servers_path=command_pytdx_servers or options["pytdx_servers_path"],
        symbols=symbols or None,
    )
    if probe_json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_live_probe_summary(
            payload,
            report_path=output_path,
            log_path=jsonl_path,
        )
    if payload.get("overall_status") == "FAIL":
        ctx.exit(1)


@main.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option("--json", "command_json_output", is_flag=True)
@click.pass_obj
def realtime(
    options: dict[str, Any],
    symbols: tuple[str, ...],
    command_json_output: bool,
) -> None:
    """Fetch realtime quotes."""

    router = _router_from_options(options)
    try:
        records = router.realtime_quotes(list(symbols))
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc
    _print_records(records, json_output=bool(options["json_output"] or command_json_output))


@main.command("full")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--json", "command_json_output", is_flag=True)
@click.pass_obj
def full(
    options: dict[str, Any],
    symbols: tuple[str, ...],
    command_json_output: bool,
) -> None:
    """Fetch full realtime quotes."""

    router = _router_from_options(options)
    try:
        records = router.full_realtime_quotes(list(symbols))
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc
    _print_records(records, json_output=bool(options["json_output"] or command_json_output))


@main.command("index")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--json", "command_json_output", is_flag=True)
@click.pass_obj
def index_realtime(
    options: dict[str, Any],
    symbols: tuple[str, ...],
    command_json_output: bool,
) -> None:
    """Fetch index realtime quotes."""

    router = _router_from_options(options)
    try:
        records = router.index_realtime(list(symbols))
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc
    _print_records(records, json_output=bool(options["json_output"] or command_json_output))


@main.command()
@click.argument("symbol")
@click.option("--period", default="1m", show_default=True)
@click.option("--count", default=240, show_default=True, type=int)
@click.option("--json", "command_json_output", is_flag=True)
@click.pass_obj
def minute(
    options: dict[str, Any],
    symbol: str,
    period: str,
    count: int,
    command_json_output: bool,
) -> None:
    """Fetch pytdx-only minute kline records."""

    router = _router_from_options(options)
    try:
        records = router.minute_kline(symbol, period=period, count=count)
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc
    _print_records(records, json_output=bool(options["json_output"] or command_json_output))


@main.command()
@click.argument("symbol")
@click.option("--count", default=120, show_default=True, type=int)
@click.option("--json", "command_json_output", is_flag=True)
@click.pass_obj
def daily(
    options: dict[str, Any],
    symbol: str,
    count: int,
    command_json_output: bool,
) -> None:
    """Fetch pytdx-only daily kline records."""

    router = _router_from_options(options)
    try:
        records = router.daily_kline(symbol, count=count)
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc
    _print_records(records, json_output=bool(options["json_output"] or command_json_output))


@main.command()
@click.argument("symbol")
@click.option("--period", default="1m", show_default=True)
@click.option("--count", default=120, show_default=True, type=int)
@click.option("--pytdx-servers", default=None, help="Override pytdx server config for this call.")
@click.option("--json", "command_json_output", is_flag=True)
@click.pass_obj
def kline(
    options: dict[str, Any],
    symbol: str,
    period: str,
    count: int,
    pytdx_servers: str | None,
    command_json_output: bool,
) -> None:
    """Fetch pytdx-only kline records through the unified API."""

    if pytdx_servers:
        options = {**options, "pytdx_servers_path": pytdx_servers}
    router = _router_from_options(options)
    try:
        records = router.kline(symbol, period=period, count=count)
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc
    _print_records(records, json_output=bool(options["json_output"] or command_json_output))


def _router_from_options(options: dict[str, Any]) -> QuoteRouter:
    try:
        return QuoteRouter.from_config(
            pytdx_servers_path=Path(options["pytdx_servers_path"]),
            source_policy_path=Path(options["source_policy_path"]),
            audit_jsonl_path=options["audit_jsonl_path"],
            audit_sqlite_path=options["audit_sqlite_path"],
        )
    except QuoteRouterError as exc:
        raise click.ClickException(_format_error(exc)) from exc


def _format_error(exc: QuoteRouterError) -> str:
    return f"[{exc.code}] {exc}"


def _parse_live_probe_symbols(extra_args: tuple[str, ...]) -> list[str]:
    symbols: list[str] = []
    args = list(extra_args)
    index = 0
    while index < len(args):
        item = args[index]
        if item == "--symbols":
            index += 1
            start_count = len(symbols)
            while index < len(args) and not args[index].startswith("-"):
                symbols.extend(_split_symbol_values(args[index]))
                index += 1
            if len(symbols) == start_count:
                raise click.ClickException("--symbols requires at least one symbol")
            continue
        if item.startswith("--symbols="):
            symbols.extend(_split_symbol_values(item.partition("=")[2]))
            index += 1
            continue
        raise click.ClickException(f"unsupported argument for source-schema-probe-live: {item}")
    return symbols


def _split_symbol_values(value: str) -> list[str]:
    return [part for part in value.replace(",", " ").split() if part]


def _print_live_probe_summary(
    payload: dict[str, Any],
    *,
    report_path: str,
    log_path: str,
) -> None:
    click.echo(f"overall_status: {payload.get('overall_status')}")
    click.echo(f"checked_at: {payload.get('checked_at')}")
    click.echo(f"report_path: {_safe_cli_path(report_path)}")
    click.echo(f"log_path: {_safe_cli_path(log_path)}")
    source_status = payload.get("source_status") or {}
    if isinstance(source_status, dict):
        for key, status in source_status.items():
            click.echo(f"{key}: {status}")
    click.echo(f"accepted_record_count: {payload.get('accepted_record_count')}")
    click.echo(f"rejected_record_count: {payload.get('rejected_record_count')}")


def _safe_cli_path(path_value: str) -> str:
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (OSError, ValueError):
        return f"<absolute-path-redacted>/{path.name}"


def _print_payload(payload: Any, *, json_output: bool) -> None:
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            click.echo(f"{key}: {value}")
    else:
        click.echo(str(payload))


def _print_records(records: list[Any], *, json_output: bool) -> None:
    rows = [record.to_dict() for record in records]
    if json_output:
        click.echo(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    columns = [
        "symbol",
        "name",
        "price",
        "close",
        "period",
        "datetime",
        "source",
        "source_level",
        "trace_id",
    ]
    columns = [
        column
        for column in columns
        if any(row.get(column) not in (None, "") for row in rows)
        or column in {"symbol", "source", "source_level", "trace_id"}
    ]
    widths = {
        column: max(
            [len(column)]
            + [len(str(row.get(column, "") or "")) for row in rows]
        )
        for column in columns
    }
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    click.echo(header)
    click.echo("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        click.echo(
            "  ".join(str(row.get(column, "") or "").ljust(widths[column]) for column in columns)
        )


main.add_command(full, "full-realtime")


if __name__ == "__main__":
    main()
