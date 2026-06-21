# Units

Adapters normalize source-specific quote units before public records are
returned. Raw source payloads may use different names and units, but the
adapter-level standard schema uses `volume_shares` and `amount_yuan`.

## QuoteRecord

| Field | Unit or convention |
|---|---|
| `price` | RMB yuan. |
| `open` | RMB yuan. |
| `high` | RMB yuan. |
| `low` | RMB yuan. |
| `pre_close` | RMB yuan when available. |
| `volume` | Standardized share count from `volume_shares`. |
| `amount` | Standardized RMB yuan amount from `amount_yuan`. |
| `datetime` | Upstream timestamp string. |

Adapter standard schema rules:

- AkShare `stock_zh_a_spot_em` raw `成交量` is in lots. It is multiplied by
  `100` before becoming `volume_shares`.
- AkShare `stock_zh_a_spot_em` raw `成交额` is already RMB yuan. It is copied to
  `amount_yuan` without dividing by `100`.
- easyquotation Tencent raw `价格/成交量(手)/成交额` is parsed as
  price/lot-volume/yuan-amount. The second part is multiplied by `100` before
  becoming `volume_shares`; the third part is copied to `amount_yuan`.
- `pct_chg` is a percent number. For example, `4.8` means `4.8%`, not `0.048`.

## KlineBar

| Field | Unit or convention |
|---|---|
| `open` | RMB yuan. |
| `high` | RMB yuan. |
| `low` | RMB yuan. |
| `close` | RMB yuan. |
| `volume` | Standardized share count from adapter standard output. |
| `amount` | Standardized RMB yuan amount from adapter standard output. |
| `datetime` | pytdx bar timestamp string. |
| `period` | Normalized request period: `1m`, `5m`, `15m`, `30m`, `60m`, or `1d`. |

The raw schema probe writes observed source fields to
`reports/latest/source_schema_probe.json` and `logs/source_schema_probe.jsonl`.
