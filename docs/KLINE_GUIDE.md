# K-line Guide

K-line APIs are pytdx-only. They do not fall back to easyquotation.
When pytdx cannot return bars, the router raises a structured error and writes
audit attempts plus `fallback_chain`.

## Supported Periods

| API | Supported periods | Source |
|---|---|---|
| `minute_kline` | `1m`, `5m`, `15m`, `30m`, `60m` | `pytdx` |
| `daily_kline` | `1d` | `pytdx` |
| `kline` | `1m`, `5m`, `15m`, `30m`, `60m`, `1d` | `pytdx` |

`kline` also accepts `daily` and `day` as aliases for `1d`.

## Python Examples

15-minute bars:

```python
import pyqauto as aq

bars = aq.minute("000001", period="15m", count=120)
```

Daily bars:

```python
bars = aq.daily("000001", count=120)
```

Unified API:

```python
minute_bars = aq.kline("000001", period="15m", count=120)
daily_bars = aq.kline("000001", period="1d", count=120)
```

## CLI Examples

```bash
pyqauto minute 000001 --period 15m --count 120 --json
pyqauto daily 000001 --count 120 --json
pyqauto kline 000001 --period 1d --count 120 --json
```

If K-line calls time out, probe the pytdx server pool and write an active local
pool:

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

Then use that pool for K-line:

```bash
pyqauto kline 000001 --period 15m --count 10 \
  --pytdx-servers config/pytdx_servers.active.local.json --json
```

The active local file is a local diagnostic result and should not be committed.
Free pytdx server availability changes by network, region, and time. A
successful probe is not a guarantee that every environment can connect later.

## Return Model

K-line APIs return `KlineBar` objects with:

- `symbol`
- `datetime`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `period`
- `source`
- `source_level`
- `fallback_from`
- `is_fallback`
- `trace_id`
- `raw` when `include_raw=True`

`datetime` is the upstream pytdx bar timestamp serialized as a string. See
[RETURN_FIELDS.md](RETURN_FIELDS.md), [UNITS.md](UNITS.md), and
[TIME_AND_TRADING_DAY.md](TIME_AND_TRADING_DAY.md).

## Unsupported Features

Adjusted bars are not supported. There is no front-adjusted or
back-adjusted K-line API unless a future release adds explicit fields, tests,
and documentation.
