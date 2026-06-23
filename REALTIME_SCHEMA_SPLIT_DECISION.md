# REALTIME_SCHEMA_SPLIT_DECISION

生成时间：2026-06-12

## 1. 决策

实时行情拆分为 `full_realtime_quotes` 与 `lite_realtime_quotes` 两级质量闸门。旧 `realtime_quotes` 保持兼容，并按 full 规则验收。

## 2. 字段规则

`full_realtime_quotes` 必需字段：

```text
code, name, last_price, pre_close, open, high, low, volume, amount,
pct_chg, source, source_latency_ms, source_status, data_timestamp
```

`lite_realtime_quotes` 必需字段：

```text
code, name, last_price, volume, amount, pct_chg,
source, source_latency_ms, source_status, data_timestamp
```

## 3. 使用边界

- 缺 `open/high/low/pre_close` 但有 `last_price/volume/amount/pct_chg` 的源，只能通过 lite gate。
- lite 不得用于需要 OHLC 或前收字段的盘中逻辑。
- lite 不得伪装为 full。
- S0 正式接入前，full/lite 使用边界冻结。

## 4. 本轮结果

| 源 | full_realtime_quotes | lite_realtime_quotes | 结论 |
|---|---:|---:|---|
| easyquotation_sina | PASS | SKIP | full primary |
| easyquotation_tencent | PASS | SKIP | full backup |
| AKShare spot | FAIL | SKIP | 不进 full 默认链路 |
| adata | FAIL | PASS | 仅 lite |

## 5. 验收

已新增 schema 与测试，验证缺少 `pre_close/open/high/low` 时 full FAIL、lite PASS。

未删除质量闸门，未降低 full realtime 字段要求，未接入 S0，未包含交易建议。
