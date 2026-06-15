# aquote-router

`aquote-router` is a lightweight A-share quote source router for research tooling.
It routes provider calls, records source attempts, and returns normalized Python
dataclasses. It is infrastructure only: it does not provide investment advice,
order execution, account login, screening, timing signals, or performance claims.

## Features

- `realtime_quotes`, `full_realtime_quotes`, and `index_realtime` route through
  `pytdx -> easyquotation_sina -> easyquotation_tencent`.
- `minute_kline`, `daily_kline`, and unified `kline` are pytdx-only.
- pytdx servers are ordered by `primary -> hot_backup -> backup`, then by
  `latency_ms`.
- `probe-pytdx` can generate a local active pytdx server pool for diagnostics.
- Return models include `source`, `source_level`, `is_fallback`,
  `fallback_from`, and `trace_id`.
- JSONL and SQLite audit logs record attempts, `fallback_chain`,
  `selected_source`, duration, record count, and final error details.
- The default test suite is offline. Live smoke checks require explicit opt-in.

## Install

```bash
python -X utf8 -m pip install aquote-router
```

Local development:

```bash
python -X utf8 -m pip install -e ".[dev,test]"
```

## Quick Start

```python
from aquote_router import QuoteRouter

router = QuoteRouter.from_config(
    pytdx_servers_path="config/pytdx_servers.example.json",
    source_policy_path="config/source_policy.example.yaml",
    audit_jsonl_path="logs/aquote_router_audit.jsonl",
    audit_sqlite_path="logs/aquote_router_audit.sqlite3",
)

records = router.realtime_quotes(["000001", "600000"])
for record in records:
    print(record.to_dict())
```

K-line examples:

```python
router.minute_kline("000001", period="15m", count=120)
router.daily_kline("000001", count=120)
router.kline("000001", period="1d", count=120)
```

## Public API

```python
router.realtime_quotes(["000001", "600000"])
router.full_realtime_quotes(["000001", "600000"])
router.index_realtime(["000001", "399001"])
router.minute_kline("000001", period="15m", count=120)
router.daily_kline("000001", count=120)
router.kline("000001", period="1d", count=120)
router.diagnose()
```

## CLI

```bash
aquote-router realtime 000001 600000
aquote-router full 000001 600000
aquote-router full-realtime 000001 600000
aquote-router index 000001 399001
aquote-router minute 000001 --period 15m --count 120
aquote-router daily 000001 --count 120
aquote-router kline 000001 --period 15m --count 120
aquote-router kline 000001 --period 1d --count 120
aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json
aquote-router diagnose --json
```

Use `--json` for complete output, especially when table columns are too wide.
CLI failures return a non-zero exit code and a structured project error code.

When K-line calls time out, first refresh a local pytdx pool:

```bash
aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then pass the active local pool explicitly:

```bash
aquote-router kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

`config/pytdx_servers.active.local.json` is an observed local diagnostic result
and should not be committed. Free pytdx server availability changes by network,
region, and time; this project does not promise that every environment can
connect at every time.

## Source Policy

Default realtime routing:

```text
realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent
index_realtime: pytdx -> easyquotation_sina -> easyquotation_tencent
```

Default K-line routing:

```text
minute_kline: pytdx only
daily_kline: pytdx only
kline: pytdx only
```

K-line APIs never fall back to easyquotation and never fabricate bars.
Realtime APIs may fall back to `easyquotation_sina` or `easyquotation_tencent`
after pytdx failures, but K-line APIs do not use easyquotation fallback.

## Core Docs

- [Quickstart](docs/QUICKSTART.md)
- [API reference](docs/API_REFERENCE.md)
- [K-line guide](docs/KLINE_GUIDE.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Return fields](docs/RETURN_FIELDS.md)
- [CLI reference](docs/CLI_REFERENCE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Error codes](docs/ERROR_CODES.md)
- [Symbol rules](docs/SYMBOL_RULES.md)
- [Units](docs/UNITS.md)
- [Source policy](docs/SOURCE_POLICY.md)
- [Audit trail](docs/AUDIT_TRAIL.md)
- [Time and trading day](docs/TIME_AND_TRADING_DAY.md)
- [Upstream license and risk](docs/UPSTREAM_LICENSE_AND_RISK.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributor adapter guide](docs/CONTRIBUTOR_ADAPTER_GUIDE.md)

## Audit Trail

Each routed call receives a `trace_id`. Audit records include:

- `api_name`
- `symbols`
- `started_at`, `finished_at`, `duration_ms`
- `selected_source`, `selected_source_level`
- `attempts`
- `fallback_chain`
- `success`
- `error_type`, `error_message`
- `record_count`

See [docs/AUDIT_TRAIL.md](docs/AUDIT_TRAIL.md).

## Risk Notice

This package does not produce market data. It calls upstream public Python
libraries and their public interfaces. Upstream data may be delayed,
unavailable, incomplete, or structurally changed. Users are responsible for
validating data quality and following the terms of each upstream project.

## License

MIT License. See [LICENSE](LICENSE).
