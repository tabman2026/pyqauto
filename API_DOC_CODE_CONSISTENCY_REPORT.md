# API / Documentation / Code Consistency Report

Date: 2026-06-15

Scope:

- `pyqauto/router.py`
- `pyqauto/models.py`
- `pyqauto/adapters/pytdx_adapter.py`
- `pyqauto/policy.py`
- `pyqauto/cli.py`
- `pyqauto/diagnostics.py`
- `docs/API_REFERENCE.md`
- `docs/KLINE_GUIDE.md`
- `docs/DATA_SOURCES.md`
- `docs/RETURN_FIELDS.md`
- `README.md`
- `examples/`
- `tests/`

## Result Matrix

| API | Code implemented | Tests | CLI | Example | Docs | Data source | Fallback rule | Result |
|---|---:|---:|---:|---:|---:|---|---|---|
| `realtime_quotes` | yes | yes | `realtime` | `realtime_quotes_demo.py` | yes | `pytdx`, `easyquotation_sina`, `easyquotation_tencent` | pytdx then easyquotation sources | PASS |
| `full_realtime_quotes` | yes | yes | `full`, `full-realtime` | `full_realtime_quotes_demo.py` | yes | `pytdx`, `easyquotation_sina`, `easyquotation_tencent` | pytdx then easyquotation sources | PASS |
| `index_realtime` | yes | yes | `index` | `index_realtime_demo.py` | yes | `pytdx`, `easyquotation_sina`, `easyquotation_tencent` | pytdx then easyquotation sources | PASS |
| `minute_kline` | yes | yes | `minute` | `minute_kline_15m_demo.py` | yes | `pytdx` | pytdx server roles only | PASS |
| `daily_kline` | yes | yes | `daily` | `daily_kline_demo.py` | yes | `pytdx` | pytdx server roles only | PASS |
| `kline` | yes | yes | `kline` | `kline_unified_demo.py` | yes | `pytdx` | pytdx server roles only | PASS |
| `diagnose` | yes | yes | `diagnose` | `diagnose_demo.py` | yes | local configuration only | not applicable | PASS |
| `status` | yes | yes | not applicable | not applicable | yes | runtime governance snapshot | not applicable | PASS |
| `health` | yes | yes | not applicable | not applicable | yes | runtime health scores | not applicable | PASS |
| `decision_trace` | yes | yes | not applicable | not applicable | yes | decision explanation | not applicable | PASS |
| `get_system_state` | yes | yes | not applicable | not applicable | yes | runtime state enum | not applicable | PASS |

## K-line Verification

- `minute_kline` supports `1m`, `5m`, `15m`, `30m`, and `60m`.
- `daily_kline` supports `1d`.
- `kline` routes minute periods to pytdx minute bars and `1d`/`daily`/`day` to pytdx daily bars.
- Unsupported periods raise `UnsupportedPeriodError`.
- K-line APIs never use easyquotation fallback.
- pytdx period mapping is centralized in `PYTDX_KLINE_PERIOD_CATEGORIES`.

## Field Verification

- Realtime APIs return `QuoteRecord`.
- K-line APIs return `KlineBar`.
- `RETURN_FIELDS.md` documents `source`, `source_level`, `fallback_from`, `is_fallback`, and `trace_id`.
- `AUDIT_TRAIL.md` documents `fallback_chain` and `selected_source`.

## Conclusion

No documented supported API is missing from code. No implemented public API is
missing from the API reference.
