# SOURCE_UNIT_POLICY

生成时间：2026-06-12  
任务：任务016｜字段单位与切源一致性冻结

源单位策略记录在 `config/source_unit_policy.json`。任务013 已出现 WARN 的字段不得写成 high confidence。

## 当前 source policy

```text
realtime_quotes:       pytdx -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes:  pytdx -> easyquotation_sina -> easyquotation_tencent
daily_kline:           akshare -> baostock
trade_calendar:        akshare -> baostock
lite_realtime_quotes:  adata
```

任务016未修改上述顺序，未新增数据源，未接入 S0/QMT/券商账户。

## 源单位假设

| source | function | price | volume | amount | pct_chg | confidence |
|---|---|---|---|---|---|---|
| `pytdx` | realtime/full/index | `yuan` | `lot` | `yuan_or_unknown` | `percent_derived` | medium |
| `easyquotation_sina` | realtime/full/index | `yuan` | `share_or_lot_to_confirm` | `yuan` | `percent_or_derived` | low |
| `easyquotation_tencent` | realtime/full/index | `yuan` | `lot_or_share_to_confirm` | `wan_yuan` | `percent_or_derived` | low |
| `akshare` | daily_kline | `yuan` | `lot` | `yuan` | `percent` | medium |
| `akshare` | index_realtime | `yuan` | `share_or_lot_to_confirm` | `yuan_or_unknown` | `percent` | low |
| `baostock` | daily_kline | `yuan` | `share` | `yuan` | `percent` | medium |
| `adata` | lite_realtime_quotes | `yuan` | `share_or_lot_to_confirm` | `yuan_or_unknown` | `percent` | low |

## 需要换算的字段

- `lot -> share`：乘以 100。
- `wan_yuan -> yuan`：乘以 10000。
- `yi_yuan -> yuan`：乘以 100000000。
- `ratio -> percent`：乘以 100。

## 无法确认单位的字段

- `easyquotation_sina.volume`
- `easyquotation_tencent.volume`
- `akshare.index_realtime.volume`
- `akshare.index_realtime.amount`
- `adata.lite_realtime_quotes.volume`
- `adata.lite_realtime_quotes.amount`
- `akshare_stock_zh_a_daily_low_frequency.volume`

这些字段不得被静默换算；如果下游要求强一致，必须 BLOCK。

## 切源规则

强校验字段：

```text
code, date, source, OHLC, last_price, volume_unit,
amount_unit, pct_chg_unit, adjust_type, data_timestamp
```

允许 WARN 不阻断：标记后的 volume 100 倍单位差异、指数成交量单位差异、`pct_chg` 轻微超阈值且价格字段一致、low confidence 单位假设。

必须 BLOCK：缺少关键字段、`daily_kline.adjust_type` 冲突、lite realtime 被用于 full realtime、强一致场景下 volume/amount 单位未知。
