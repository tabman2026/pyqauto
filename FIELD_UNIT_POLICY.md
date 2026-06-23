# FIELD_UNIT_POLICY

生成时间：2026-06-12  
任务：任务016｜字段单位与切源一致性冻结

本文件冻结字段单位、口径、派生规则和阻断边界。本文只描述数据字段层，不包含任何交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。

## 标准字段单位

| 字段 | 标准单位/口径 | 规则 |
|---|---|---|
| `open/high/low/close/pre_close/last_price` | `yuan` | 人民币元；保留 `raw_*` 与 `*_normalized`。 |
| `volume` | `share` | 源返回“手”时乘以 100；源返回“股”时不换算；未知单位不强行换算并写入 `field_warnings`。 |
| `amount` | `yuan` | `yuan` 不换算，`wan_yuan` 乘以 10000，`yi_yuan` 乘以 100000000；未知单位不强行换算。 |
| `pct_chg` | `percent` | `1.23` 表示 `1.23%`；ratio 口径乘以 100；由价格推导时标记 `pct_chg_derived=true`。 |
| `adjust_type` | `none/qfq/hfq/unknown` | `daily_kline` 必须携带；不同复权类型不得直接比较。 |
| `date/time/data_timestamp/request_time` | ISO/固定格式 | `date=YYYY-MM-DD`，`time=HH:MM:SS`，timestamp 为 ISO 格式。 |

## 必须保留的元数据

`volume`：

```text
raw_volume, raw_volume_unit, volume, volume_unit,
volume_normalized, volume_normalized_unit,
volume_unit_source, volume_unit_confidence
```

`amount`：

```text
raw_amount, raw_amount_unit, amount, amount_unit,
amount_normalized, amount_normalized_unit,
amount_unit_source, amount_unit_confidence
```

`pct_chg`：

```text
pct_chg, pct_chg_unit, pct_chg_source,
pct_chg_derived, pct_chg_formula, pct_chg_warning
```

来源字段必须保留：

```text
source, source_latency_ms, source_status, field_warnings
```

## 派生字段

`pytdx.pct_chg` 由本项目按以下公式推导：

```text
(close - pre_close) / pre_close * 100
```

实时数据使用 `last_price` 作为公式中的 `close`。派生字段不得伪装成源原始字段，必须记录 `pct_chg_derived=true` 与 `pct_chg_formula`。

## WARN 字段

- `daily_kline.volume`：AKShare 与 Baostock 已发现 100 倍单位口径差异，按 `lot -> share` 标准化，并保留 WARN 背景。
- `daily_kline.pct_chg`：任务013发现跨源超阈值差异，保留 WARN，不用于任何交易判断。
- `index_realtime.volume`：跨源存在单位比例差异，允许 WARN，不静默覆盖。
- `easyquotation_sina/easyquotation_tencent` 的部分实时成交量单位仍为 low confidence，未知时不强行换算。
- `adata` 仅可用于 `lite_realtime_quotes`，不得升级为 full。

## 切源强校验

切源时必须校验字段存在性、字段单位、字段类型、价格差异、成交量差异、成交额差异、`pct_chg` 差异、`data_timestamp` 差异、`adjust_type` 一致性、`field_warnings` 是否扩大。

必须 BLOCK：

- OHLC 缺失。
- `last_price` 缺失。
- `code`、`date`、`source` 缺失。
- `daily_kline.adjust_type` 冲突且未阻断。
- `volume` 或 `amount` 单位未知且下游要求强一致。
- `lite_realtime_quotes` 被用于 full realtime。

允许 WARN：

- 已知 100 倍 volume 单位差异已标记，且不参与强一致用途。
- 指数成交量单位差异已标记。
- `pct_chg` 小幅超阈值但价格字段一致。
- timestamp lag 接近可接受边界。

## 文件与实现

- 策略配置：`config/field_unit_policy.json`
- 源单位假设：`config/source_unit_policy.json`
- 单位策略读取：`astock_source_router/core/unit_policy.py`
- 单位标准化：`astock_source_router/core/unit_normalizer.py`
- 单位检查脚本：`scripts/check_unit_consistency.py`
