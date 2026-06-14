"""Command line interface for aquote-router."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from aquote_router import __version__
from aquote_router.exceptions import QuoteRouterError
from aquote_router.router import QuoteRouter

DEFAULT_PYTDX_SERVERS = "config/pytdx_servers.example.json"
DEFAULT_SOURCE_POLICY = "config/source_policy.example.yaml"


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
@click.pass_obj
def diagnose(options: dict[str, Any]) -> None:
    """Show local configuration summary without provider connections."""

    router = _router_from_options(options)
    _print_payload(router.diagnose(), json_output=options["json_output"])


@main.command()
@click.argument("symbols", nargs=-1, required=True)
@click.pass_obj
def realtime(options: dict[str, Any], symbols: tuple[str, ...]) -> None:
    """Fetch realtime quotes."""

    router = _router_from_options(options)
    try:
        records = router.realtime_quotes(list(symbols))
    except QuoteRouterError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_records(records, json_output=options["json_output"])


@main.command("full-realtime")
@click.argument("symbols", nargs=-1, required=True)
@click.pass_obj
def full_realtime(options: dict[str, Any], symbols: tuple[str, ...]) -> None:
    """Fetch full realtime quotes."""

    router = _router_from_options(options)
    try:
        records = router.full_realtime_quotes(list(symbols))
    except QuoteRouterError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_records(records, json_output=options["json_output"])


@main.command("index")
@click.argument("symbols", nargs=-1, required=True)
@click.pass_obj
def index_realtime(options: dict[str, Any], symbols: tuple[str, ...]) -> None:
    """Fetch index realtime quotes."""

    router = _router_from_options(options)
    try:
        records = router.index_realtime(list(symbols))
    except QuoteRouterError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_records(records, json_output=options["json_output"])


@main.command()
@click.argument("symbol")
@click.option("--period", default="1m", show_default=True)
@click.pass_obj
def minute(options: dict[str, Any], symbol: str, period: str) -> None:
    """Fetch pytdx-only minute kline records."""

    router = _router_from_options(options)
    try:
        records = router.minute_kline(symbol, period=period)
    except QuoteRouterError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_records(records, json_output=options["json_output"])


def _router_from_options(options: dict[str, Any]) -> QuoteRouter:
    try:
        return QuoteRouter.from_config(
            pytdx_servers_path=Path(options["pytdx_servers_path"]),
            source_policy_path=Path(options["source_policy_path"]),
            audit_jsonl_path=options["audit_jsonl_path"],
            audit_sqlite_path=options["audit_sqlite_path"],
        )
    except QuoteRouterError as exc:
        raise click.ClickException(str(exc)) from exc


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
    columns = ["symbol", "name", "price", "datetime", "source", "source_level"]
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


if __name__ == "__main__":
    main()
