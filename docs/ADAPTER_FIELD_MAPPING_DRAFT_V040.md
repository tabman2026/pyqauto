# v0.4.0 Adapter Field Mapping Draft

This is a mapping draft for candidate adapters only. The candidates here are
not officially supported by the current package and are not in the default
fallback chain.

Related v0.4.0 gates:

- [CANDIDATE_NORMALIZE_CONTRACT_V040.md](CANDIDATE_NORMALIZE_CONTRACT_V040.md)
- [V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md](V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md)

Standard model note: the current dataclasses expose `volume` and `amount`.
These fields carry `volume_shares` and `amount_yuan` semantics after adapter
normalization. Candidate normalizers are test-only contracts, not public
adapter APIs.

## efinance Realtime -> pyqauto QuoteRecord

| 上游字段 | 上游含义 | 上游单位 | 标准字段 | 标准单位 | 是否核心字段 | 缺失处理 | 备注 |
|---|---|---|---|---|---|---|---|
| `股票代码` | Security code | text | `symbol` | text | Yes | Reject row | Normalize to six-digit symbol. |
| `股票名称` | Security name | text | `name` | text | No | Set `None` | Keep upstream display name. |
| `最新价` | Last traded price | price | `price` | yuan per share or fund unit | Yes | Reject row | Accept only numeric values. |
| `今开` | Open price | price | `open` | yuan per share or fund unit | No | Set `None` | Optional for quote output. |
| `最高` | High price | price | `high` | yuan per share or fund unit | No | Set `None` | Optional for quote output. |
| `最低` | Low price | price | `low` | yuan per share or fund unit | No | Set `None` | Optional for quote output. |
| `昨日收盘` | Previous close | price | `pre_close` | yuan per share or fund unit | No | Set `None` | Required before computing any derived change. |
| `成交量` | Traded volume | unknown | `volume` (`volume_shares`) | shares | Yes | Reject until unit rule exists | Do not guess shares versus lots. |
| `成交额` | Traded amount | unknown | `amount` (`amount_yuan`) | yuan | Yes | Reject until unit rule exists | Examples look amount-like, but admission keeps unit unknown. |
| `更新时间` | Update timestamp | datetime string | `datetime` | ISO-like string | No | Set `None` | Prefer upstream timestamp when present. |
| source literal | Adapter name | text | `source` | text | Yes | Fill `efinance_candidate` | Candidate-only source value; not formal support. |

## efinance Kline -> pyqauto KlineBar

| 上游字段 | 上游含义 | 上游单位 | 标准字段 | 标准单位 | 是否核心字段 | 缺失处理 | 备注 |
|---|---|---|---|---|---|---|---|
| `股票代码` | Security code | text | `symbol` | text | Yes | Reject bar | Normalize to six-digit symbol. |
| `日期` | Bar timestamp | date or datetime string | `datetime` | ISO-like string | Yes | Reject bar | Minute bars include time; daily bars use date. |
| `开盘` | Open price | price | `open` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `最高` | High price | price | `high` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `最低` | Low price | price | `low` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `收盘` | Close price | price | `close` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `成交量` | Traded volume | unknown | `volume` (`volume_shares`) | shares | Yes | Reject until unit rule exists | Unit must be proven by live probe. |
| `成交额` | Traded amount | unknown | `amount` (`amount_yuan`) | yuan | Yes | Reject until unit rule exists | Unit must be proven by live probe. |
| `klt` request value | Bar period | integer enum | `period` | pyqauto period string | Yes | Reject bar | `1/5/15/30/60/101/102/103` map to `1m/5m/15m/30m/60m/1d/1w/1mo`. |
| `fqt` request value | Adjustment mode | integer enum | raw metadata | `none/forward/backward` | No | Preserve in raw metadata | `0/1/2` from official docs/source. |

## baostock Kline -> pyqauto KlineBar

| 上游字段 | 上游含义 | 上游单位 | 标准字段 | 标准单位 | 是否核心字段 | 缺失处理 | 备注 |
|---|---|---|---|---|---|---|---|
| `code` | Security code with market prefix | text | `symbol` | text | Yes | Reject bar | `sh.600000`/`sz.000001` need normalization. |
| `date` | Bar date | date string | `datetime` | ISO-like string | Yes | Reject bar | Combine with `time` for minute bars when present. |
| `time` | Minute timestamp | compact datetime string | `datetime` | ISO-like string | Yes for minute bars | Reject minute bar | Daily bars do not include this field. |
| `open` | Open price | price | `open` | yuan per share or fund unit | Yes | Reject bar | Source returns strings. |
| `high` | High price | price | `high` | yuan per share or fund unit | Yes | Reject bar | Source returns strings. |
| `low` | Low price | price | `low` | yuan per share or fund unit | Yes | Reject bar | Source returns strings. |
| `close` | Close price | price | `close` | yuan per share or fund unit | Yes | Reject bar | Source returns strings. |
| `volume` | Traded volume | unknown | `volume` (`volume_shares`) | shares | Yes | Reject until unit rule exists | Do not infer from field name alone. |
| `amount` | Traded amount | unknown | `amount` (`amount_yuan`) | yuan | Yes | Reject until unit rule exists | Do not infer from field name alone. |
| `frequency` request value | Bar period | string enum | `period` | pyqauto period string | Yes | Reject bar | `d/5/15/30/60/w/m` need explicit mapping tests. |
| `adjustflag` | Adjustment mode | string enum | raw metadata | `none/forward/backward` | No | Preserve in raw metadata | `"3"` none and `"2"` forward confirmed; other values need more research. |
| source literal | Adapter name | text | `source` | text | Yes | Fill `baostock_candidate` | Candidate-only source value; not formal support. |

## mootdx Quote -> pyqauto QuoteRecord

| 上游字段 | 上游含义 | 上游单位 | 标准字段 | 标准单位 | 是否核心字段 | 缺失处理 | 备注 |
|---|---|---|---|---|---|---|---|
| `code` | Security code | text | `symbol` | text | Yes | Reject row | Derived from tdxpy/pytdx-style quote output. |
| `name` | Security name | text | `name` | text | No | Set `None` | Present only when upstream includes it. |
| `price` | Last price | price | `price` | yuan per share or fund unit | Yes | Reject row | Numeric only. |
| `open` | Open price | price | `open` | yuan per share or fund unit | No | Set `None` | Optional for quote output. |
| `high` | High price | price | `high` | yuan per share or fund unit | No | Set `None` | Optional for quote output. |
| `low` | Low price | price | `low` | yuan per share or fund unit | No | Set `None` | Optional for quote output. |
| `last_close` or `pre_close` | Previous close | price | `pre_close` | yuan per share or fund unit | No | Set `None` | Exact column can vary by tdxpy version. |
| `vol` | Traded volume | unknown | `volume` (`volume_shares`) | shares | Yes | Reject until unit rule exists | Compare with current pytdx adapter before admission. |
| `amount` | Traded amount | unknown | `amount` (`amount_yuan`) | yuan | Yes | Reject until unit rule exists | Compare with current pytdx adapter before admission. |
| source literal | Adapter name | text | `source` | text | Yes | Fill `mootdx_candidate` | Candidate-only source value; not formal support. |

## mootdx Kline -> pyqauto KlineBar

| 上游字段 | 上游含义 | 上游单位 | 标准字段 | 标准单位 | 是否核心字段 | 缺失处理 | 备注 |
|---|---|---|---|---|---|---|---|
| request symbol | Security code | text | `symbol` | text | Yes | Reject bar | Normalize from request context. |
| `datetime` | Bar timestamp | datetime | `datetime` | ISO-like string | Yes | Reject bar | Some outputs also expose year/month/day/hour/minute columns. |
| `open` | Open price | price | `open` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `high` | High price | price | `high` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `low` | Low price | price | `low` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `close` | Close price | price | `close` | yuan per share or fund unit | Yes | Reject bar | Numeric only. |
| `vol` | Traded volume | unknown | `volume` (`volume_shares`) | shares | Yes | Reject until unit rule exists | Treat as pytdx-family raw field, not automatically standard. |
| `amount` | Traded amount | unknown | `amount` (`amount_yuan`) | yuan | Yes | Reject until unit rule exists | Treat as pytdx-family raw field, not automatically standard. |
| `frequency` request value | Bar period | integer enum | `period` | pyqauto period string | Yes | Reject bar | Use the same mapping contract as pytdx only after comparison tests. |
| `adjust` request value | Adjustment mode | string enum | raw metadata | `none/forward/backward` | No | Preserve in raw metadata | `qfq/hfq` docs exist, but semantics require validation. |
| source literal | Adapter name | text | `source` | text | Yes | Fill `mootdx_candidate` | Candidate-only source value; not formal support. |

## Draft Acceptance Rule

Any candidate row with a missing core field or `unknown` unit on volume/amount
must be rejected by schema guard and must not enter public records.
