# SOURCE_SWITCH_CONSISTENCY_REPORT

- generated_at: `2026-06-12T13:23:38.353767+00:00`
- overall_status: `WARN`
- has_block: `False`
- mode: `fixture`
- source policy changed: `no`
- raw source data overwritten: `no`

## Switch Paths

| path | feature | status | block | issue_count |
|---|---|---:|---:|---:|
| `pytdx -> easyquotation_sina` | `realtime_quotes` | `WARN` | `False` | `3` |
| `easyquotation_sina -> easyquotation_tencent` | `full_realtime_quotes` | `WARN` | `False` | `3` |
| `akshare -> baostock` | `daily_kline` | `PASS` | `False` | `0` |
| `akshare_hist -> akshare_stock_zh_a_daily_low_frequency` | `daily_kline` | `WARN` | `False` | `2` |

## Block Rules

- BLOCK when OHLC, last_price, code, date, or source is missing.
- BLOCK when daily_kline adjust_type conflicts across a switch path.
- BLOCK when lite_realtime_quotes is used as full_realtime_quotes.
- WARN when known unit differences are marked and not required for strong consistency.

## Gate

- source switch consistency: `PASS` or `WARN without BLOCK` is acceptable for task016.
- continue 5-day stability watch: `yes` if no BLOCK exists.
- allow S0 production: `no`.
