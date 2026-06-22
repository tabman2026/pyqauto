# API Reference

## Simple API

```python
import pyqauto as aq

aq.quote("000001")                         # one realtime quote
aq.quotes(["000001", "600000"])            # realtime quotes
aq.full_quotes(["000001", "600000"])       # full realtime quotes
aq.index(["000001", "399001"])             # index realtime quotes
aq.minute("000001", period="15m", count=120)
aq.daily("000001", count=120)
aq.kline("000001", period="1d", count=120)
aq.diagnose()
```

`aq.configure(...)` is optional and only needed for custom config paths or audit
outputs.

## `QuoteRouter.from_config`

```python
QuoteRouter.from_config(
    *,
    pytdx_servers_path: str | Path | None = None,
    source_policy_path: str | Path | None = None,
    audit_jsonl_path: str | Path | None = None,
    audit_sqlite_path: str | Path | None = None,
) -> QuoteRouter
```

Loads bundled default pytdx server config and source policy unless explicit
paths are provided. Realtime adapters and optional audit writers are initialized
from the resolved configuration.

## `realtime_quotes`

```python
router.realtime_quotes(["000001", "600000"], include_raw=False) -> list[QuoteRecord]
```

Source order: `pytdx -> easyquotation_sina -> easyquotation_tencent`.

## `full_realtime_quotes`

```python
router.full_realtime_quotes(["000001", "600000"], include_raw=False) -> list[QuoteRecord]
```

Source order: `pytdx -> easyquotation_sina -> easyquotation_tencent`.

## `index_realtime`

```python
router.index_realtime(["000001", "399001"], include_raw=False) -> list[QuoteRecord]
```

Source order: `pytdx -> easyquotation_sina -> easyquotation_tencent`.

## `minute_kline`

```python
router.minute_kline("000001", period="15m", count=120, include_raw=False) -> list[KlineBar]
```

Supported periods: `1m`, `5m`, `15m`, `30m`, `60m`.
Source: `pytdx` only. No easyquotation fallback.

## `daily_kline`

```python
router.daily_kline("000001", count=120, include_raw=False) -> list[KlineBar]
```

Supported period: `1d`. Source: `pytdx` only. No easyquotation fallback.

## `kline`

```python
router.kline("000001", period="1d", count=120, include_raw=False) -> list[KlineBar]
```

Unified K-line entry point:

- `1m`, `5m`, `15m`, `30m`, `60m` route to pytdx minute bars.
- `1d`, `daily`, and `day` route to pytdx daily bars.
- Other periods raise `UnsupportedPeriodError`.

Source: `pytdx` only. No easyquotation fallback.

## `diagnose`

```python
router.diagnose() -> dict
```

Returns local router configuration without connecting to upstream providers.

CLI equivalent:

```bash
pyqauto diagnose --json
```

## Runtime Governance

```python
router.status() -> dict
router.health() -> dict
router.decision_trace() -> dict
router.get_system_state() -> SystemState
```

These read-only inspection APIs expose the L5 runtime governance layer:

- `status()` returns the current system state, health scores, latest decision
  trace, and state history.
- `health()` returns `pytdx_health_score`, `akshare_health_score`,
  `efinance_health_score`, and `overall_data_health_score`.
- `decision_trace()` explains the latest decision with failed sources, fallback
  chain, and schema validation status.
- `get_system_state()` returns one of `NORMAL`, `DEGRADED`, `READONLY`,
  `BLOCKED`, or `RECOVERY`.

## Return Values

Realtime APIs return `QuoteRecord`. K-line APIs return `KlineBar`. Both models
support `to_dict(include_raw=False)`.

See [RETURN_FIELDS.md](RETURN_FIELDS.md).

## Exceptions

Public exceptions inherit from `QuoteRouterError` and include a stable `code`.
Common exceptions:

- `ConfigurationError`
- `SourcePolicyError`
- `SourceUnavailableError`
- `NoAvailableSourceError`
- `UnsupportedSymbolError`
- `UnsupportedPeriodError`

See [ERROR_CODES.md](ERROR_CODES.md).
