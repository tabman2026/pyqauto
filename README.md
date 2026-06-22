# pyqauto

pyqauto 是一个面向 A 股行情获取的 Python 行情源自动选择工具，支持 pytdx 主备切换、easyquotation fallback、实时行情、分钟K线、日K、统一 kline 接口、source policy 和 JSONL / SQLite 审计追踪。

Python A-share quote auto-selector with pytdx failover, easyquotation fallback, K-line APIs and audit trail.

```bash
python -X utf8 -m pip install pyqauto -i https://pypi.org/simple
```

```python
from pyqauto import QuoteRouter
```

```bash
pyqauto realtime 000001 600000
pyqauto kline 000001 --period 15m --count 10
pyqauto probe-pytdx --json
```

本项目不提供投资建议，不接入下单或执行系统，不保证公开免费行情源 100% 准确、实时、完整、可用。

[![PyPI version](https://img.shields.io/pypi/v/pyqauto.svg)](https://pypi.org/project/pyqauto/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyqauto.svg)](https://pypi.org/project/pyqauto/)
[![CI](https://github.com/tabman2026/pyqauto/actions/workflows/ci.yml/badge.svg)](https://github.com/tabman2026/pyqauto/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/tabman2026/pyqauto?display_name=tag)](https://github.com/tabman2026/pyqauto/releases)

It is designed for research scripts that need A股行情, A股实时行情, A股K线,
分钟K线, 15分钟K线, 日K, source policy, 数据源 fallback, 行情审计, `trace_id`,
JSONL, and SQLite audit records in one small Python package. Realtime routing
uses pytdx first, then AkShare Eastmoney spot, easyquotation Sina, and
easyquotation Tencent fallback according to policy.

Boundary: this project is data access infrastructure only. It does not provide investment advice,
account login, order execution, screening, timing signals, or performance claims.

## 中文文档

- 中文快速开始：[README.zh-CN.md](README.zh-CN.md)
- 新手从这里开始：[docs/NEW_USER_START_HERE.md](docs/NEW_USER_START_HERE.md)
- K线使用指南：[docs/KLINE_GUIDE.md](docs/KLINE_GUIDE.md)
- 数据源说明：[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)
- 常见问题排查：[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## Developer Entry

- Beginner developer guide: [docs/BEGINNER_DEVELOPER_GUIDE.md](docs/BEGINNER_DEVELOPER_GUIDE.md)
- Upstream commons research: [docs/UPSTREAM_COMMONS_RESEARCH.md](docs/UPSTREAM_COMMONS_RESEARCH.md)
- Adapter template: [docs/ADAPTER_TEMPLATE.md](docs/ADAPTER_TEMPLATE.md)
- Field mapping template: [docs/FIELD_MAPPING_TEMPLATE.md](docs/FIELD_MAPPING_TEMPLATE.md)
- Unit rules for adapters: [docs/UNIT_RULES_FOR_ADAPTERS.md](docs/UNIT_RULES_FOR_ADAPTERS.md)
- When to release: [docs/WHEN_TO_RELEASE.md](docs/WHEN_TO_RELEASE.md)
- v0.4.0 adapter candidate review entry:
  [review](docs/ADAPTER_CANDIDATE_REVIEW_V040.md),
  [field mapping draft](docs/ADAPTER_FIELD_MAPPING_DRAFT_V040.md),
  [unit rules draft](docs/ADAPTER_UNIT_RULES_DRAFT_V040.md), and
  [source policy draft](docs/SOURCE_POLICY_DRAFT_V040.md).
- v0.4.0 candidate normalize contract:
  [CANDIDATE_NORMALIZE_CONTRACT_V040.md](docs/CANDIDATE_NORMALIZE_CONTRACT_V040.md)
  and
  [V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md](docs/V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md).
  These are candidate adapter review documents. Candidate normalizers are
  test-only contracts, not public adapter APIs. These drafts do not mean the current version supports these data sources.
  Candidate sources do not enter the default fallback chain.

English start here: [docs/NEW_USER_START_HERE.md](docs/NEW_USER_START_HERE.md)

Data source policy: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

Issue guide: [docs/ISSUE_GUIDE.md](docs/ISSUE_GUIDE.md)

Examples: [realtime](examples/realtime_quotes_demo.py),
[15m K-line](examples/minute_kline_15m_demo.py), and
[daily K-line](examples/daily_kline_demo.py)

## Install

```bash
python -X utf8 -m pip install pyqauto
```

## Minimal Realtime Quote

```python
import pyqauto as aq

record = aq.quote("000001")
print(record.to_dict())
```

Default source policy and pytdx server config are bundled in the package.
Import and call functions directly. No local config files are required.

## Minimal 15m K-line

```python
bars = aq.kline("000001", period="15m", count=120)
print(bars[0].to_dict())
```

## K-line Timeout Check

K-line APIs are pytdx-only. If a K-line call times out, first probe the pytdx
server pool for the current network:

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then pass the active local pool explicitly:

```bash
pyqauto kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

`config/pytdx_servers.active.local.json` is a local diagnostic result and should
not be committed.

## Features

- `realtime_quotes` and `full_realtime_quotes` route through
  `pytdx -> akshare_em_spot -> easyquotation_sina -> easyquotation_tencent`.
- `index_realtime` routes through `pytdx -> easyquotation_sina ->
  easyquotation_tencent`.
- `minute_kline`, `daily_kline`, and unified `kline` are pytdx-only.
- Source adapters expose `fetch_raw()`, `inspect_raw_schema()`,
  `normalize_to_standard()`, and `validate_standard_output()`.
- Raw schema probes write UTF-8 JSON to `reports/latest/source_schema_probe.json`
  and UTF-8 JSONL to `logs/source_schema_probe.jsonl`.
- Live schema probes write UTF-8 JSON to
  `reports/latest/source_schema_probe_live.json` and UTF-8 JSONL to
  `logs/source_schema_probe_live.jsonl` when explicitly run with
  `pyqauto source-schema-probe-live --json`.
- Schema drift guards mark missing or renamed core fields as `schema_drift` or
  `field_missing`; invalid rows are not exposed as public records.
- AkShare volume is converted from lots to shares, AkShare amount remains yuan,
  and Tencent composite volume/amount fields are parsed before validation.
- pytdx servers are ordered by `primary -> hot_backup -> backup`, then by
  `latency_ms`.
- `probe-pytdx` can generate a local active pytdx server pool for diagnostics.
- Return models include `source`, `source_level`, `is_fallback`,
  `fallback_from`, and `trace_id`.
- JSONL and SQLite audit logs record attempts, `fallback_chain`,
  `selected_source`, duration, record count, and final error details.
- Runtime governance APIs expose `status()`, `health()`, `decision_trace()`,
  and `get_system_state()` for system state, health scores, fallback
  explanations, and schema validation status.
- The default test suite is offline. Live smoke checks require explicit opt-in.

See [docs/SOURCE_SCHEMA_LIVE_PROBE.md](docs/SOURCE_SCHEMA_LIVE_PROBE.md) for
live probe status, unit rules, and troubleshooting.

Local development:

```bash
python -X utf8 -m pip install -e ".[dev,test]"
```

## Quick Start

```python
import pyqauto as aq

aq.configure(
    audit_jsonl_path="logs/pyqauto_audit.jsonl",
    audit_sqlite_path="logs/pyqauto_audit.sqlite3",
)

records = aq.quotes(["000001", "600000"])
for record in records:
    print(record.to_dict())
```

K-line examples:

```python
aq.minute("000001", period="15m", count=120)
aq.daily("000001", count=120)
aq.kline("000001", period="1d", count=120)
```

## Public API

```python
aq.quote("000001")
aq.quotes(["000001", "600000"])
aq.full_quotes(["000001", "600000"])
aq.index(["000001", "399001"])
aq.minute("000001", period="15m", count=120)
aq.daily("000001", count=120)
aq.kline("000001", period="1d", count=120)
aq.diagnose()
```

For advanced use, `from pyqauto import QuoteRouter` remains available.
Advanced router instances also expose read-only runtime governance methods:
`router.status()`, `router.health()`, `router.decision_trace()`, and
`router.get_system_state()`.

## CLI

```bash
pyqauto realtime 000001 600000
pyqauto full 000001 600000
pyqauto full-realtime 000001 600000
pyqauto index 000001 399001
pyqauto minute 000001 --period 15m --count 120
pyqauto daily 000001 --count 120
pyqauto kline 000001 --period 15m --count 120
pyqauto kline 000001 --period 1d --count 120
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
pyqauto diagnose --json
```

Use `--json` for complete output, especially when table columns are too wide.
CLI failures return a non-zero exit code and a structured project error code.

When K-line calls time out, first refresh a local pytdx pool:

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then pass the active local pool explicitly:

```bash
pyqauto kline 000001 --period 15m --count 10 \
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
- [Beginner developer guide](docs/BEGINNER_DEVELOPER_GUIDE.md)
- [Upstream commons research](docs/UPSTREAM_COMMONS_RESEARCH.md)
- [Adapter template](docs/ADAPTER_TEMPLATE.md)
- [Field mapping template](docs/FIELD_MAPPING_TEMPLATE.md)
- [Unit rules for adapters](docs/UNIT_RULES_FOR_ADAPTERS.md)
- [When to release](docs/WHEN_TO_RELEASE.md)
- [v0.4.0 adapter candidate review](docs/ADAPTER_CANDIDATE_REVIEW_V040.md)
- [v0.4.0 adapter field mapping draft](docs/ADAPTER_FIELD_MAPPING_DRAFT_V040.md)
- [v0.4.0 adapter unit rules draft](docs/ADAPTER_UNIT_RULES_DRAFT_V040.md)
- [v0.4.0 source policy draft](docs/SOURCE_POLICY_DRAFT_V040.md)
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
