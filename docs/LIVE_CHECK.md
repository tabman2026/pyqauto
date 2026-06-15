# aquote-router Live Check

`scripts/live_check.py` is a local manual diagnostic tool for aquote-router
real data sources. It is intentionally kept outside GitHub Actions CI because
it connects to public upstream quote sources and may fail because of network,
provider, market-hour, or upstream availability conditions.

## Scope

The live check covers:

- `realtime_quotes`
- `full_realtime_quotes`
- `index_realtime`
- `minute_kline` with `1m`, `15m`, and `60m`
- `daily_kline`
- unified `kline` with `15m` and `1d`
- `aquote-router diagnose --json`

Test symbols are `000001`, `600000`, and `399001`.

Realtime APIs use the configured fallback chain:

```text
pytdx -> easyquotation_sina -> easyquotation_tencent
```

K-line APIs are pytdx-only and are accepted only when they return
`source=pytdx`. The tool does not fabricate bars and does not fall back to
easyquotation for K-line data.

## Run

On Windows, set the code page before running Python:

```bat
chcp 65001 >nul
python -X utf8 scripts\live_check.py --json
```

After refreshing a local pytdx server pool, pass the generated local config:

```bat
chcp 65001 >nul
python -X utf8 scripts\live_check.py --json --config config\pytdx_servers.active.local.json
```

The same command with POSIX-style paths is:

```bash
python -X utf8 scripts/live_check.py --json --config config/pytdx_servers.active.local.json
```

The script writes:

- `LIVE_CHECK_REPORT.md`
- `LIVE_CHECK_SUMMARY.json`
- `LIVE_CHECK_LOG.txt`
- `logs/live_check_audit.jsonl`
- `logs/live_check_audit.sqlite3`

All JSON and JSONL files are written as UTF-8 with `ensure_ascii=False`.

`config\pytdx_servers.active.local.json` is a local diagnostic input generated
by `aquote-router probe-pytdx` or `scripts\pytdx_server_probe.py`. It is
intentionally ignored by git because free pytdx server availability changes by
network, region, and time. A local active pool is an observed diagnostic result,
not a long-term stable official server list.

If K-line calls time out, refresh the local pool first:

```bat
aquote-router probe-pytdx --json --output config\pytdx_servers.active.local.json
```

Then run K-line checks with the active local pool:

```bat
aquote-router kline 000001 --period 15m --count 10 --pytdx-servers config\pytdx_servers.active.local.json --json
```

## CLI Checks

When the `aquote-router` console script is available, the live check also runs
CLI diagnostics with explicit audit paths:

```bat
aquote-router diagnose --json
aquote-router realtime 000001 600000 --json
aquote-router index 399001 --json
aquote-router kline 000001 --period 15m --count 10 --json
aquote-router kline 000001 --period 1d --count 10 --json
```

## Boundaries

This tool is not an API service, not a data redistribution service, and not a
trading integration. It does not store cookies, tokens, account credentials, or
brokerage login state. It does not output trading plans, candidate pools,
position sizing, timing signals, return promises, win-rate claims, or investment
advice.

Live source failures are valid diagnostic outcomes. The report records the
observed error reason, source attempts, audit status, and acceptance result.
