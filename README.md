# aquote-router

[![PyPI version](https://img.shields.io/pypi/v/aquote-router.svg)](https://pypi.org/project/aquote-router/)
[![Python versions](https://img.shields.io/pypi/pyversions/aquote-router.svg)](https://pypi.org/project/aquote-router/)
[![CI](https://github.com/tabman2026/aquote-router/actions/workflows/ci.yml/badge.svg)](https://github.com/tabman2026/aquote-router/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/tabman2026/aquote-router?display_name=tag)](https://github.com/tabman2026/aquote-router/releases)

aquote-router 是一个面向 A 股量化研究的轻量行情源路由器，支持 pytdx 主备切换、easyquotation fallback、实时行情、分钟K线、日K、统一 kline 接口、source policy 和 JSONL / SQLite 审计追踪。

A-share quote source router with pytdx failover, easyquotation fallback, K-line APIs and audit trail.

It is designed for research scripts that need A股行情, A股实时行情, A股K线,
分钟K线, 15分钟K线, 日K, source policy, 数据源 fallback, 行情审计, `trace_id`,
JSONL, and SQLite audit records in one small Python package. Realtime routing
uses pytdx first, then easyquotation Sina and Tencent fallback according to
policy.

Boundary: this project is data access infrastructure only. It does not provide investment advice,
account login, order execution, screening, timing signals, or performance claims.

## 中文文档

- 中文快速开始：[README.zh-CN.md](README.zh-CN.md)
- 新手从这里开始：[docs/NEW_USER_START_HERE.md](docs/NEW_USER_START_HERE.md)
- K线使用指南：[docs/KLINE_GUIDE.md](docs/KLINE_GUIDE.md)
- 数据源说明：[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)
- 常见问题排查：[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

English start here: [docs/NEW_USER_START_HERE.md](docs/NEW_USER_START_HERE.md)

Data source policy: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

Issue guide: [docs/ISSUE_GUIDE.md](docs/ISSUE_GUIDE.md)

Examples: [realtime](examples/realtime_quotes_demo.py),
[15m K-line](examples/minute_kline_15m_demo.py), and
[daily K-line](examples/daily_kline_demo.py)

## Install

```bash
python -X utf8 -m pip install aquote-router
```

## Minimal Realtime Quote

```python
from aquote_router import QuoteRouter

router = QuoteRouter.from_config(
    pytdx_servers_path="config/pytdx_servers.example.json",
    source_policy_path="config/source_policy.example.yaml",
    audit_jsonl_path="logs/aquote_router_audit.jsonl",
    audit_sqlite_path="logs/aquote_router_audit.sqlite3",
)

records = router.realtime_quotes(["000001"])
print(records[0].to_dict())
```

## Minimal 15m K-line

```python
bars = router.minute_kline("000001", period="15m", count=120)
print(bars[0].to_dict())
```

## K-line Timeout Check

K-line APIs are pytdx-only. If a K-line call times out, first probe the pytdx
server pool for the current network:

```bash
aquote-router probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then pass the active local pool explicitly:

```bash
aquote-router kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

`config/pytdx_servers.active.local.json` is a local diagnostic result and should
not be committed.

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
- [Start here](docs/NEW_USER_START_HERE.md)
- [API reference](docs/API_REFERENCE.md)
- [K-line guide](docs/KLINE_GUIDE.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Issue guide](docs/ISSUE_GUIDE.md)
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
- [Maintainer checklist](docs/MAINTAINER_CHECKLIST.md)

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
