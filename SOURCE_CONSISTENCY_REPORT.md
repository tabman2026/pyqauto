# SOURCE_CONSISTENCY_REPORT

生成时间：2026-06-12

数据来源：`logs/source_consistency_report.json`  
运行方式：`ENABLE_SOURCE_CONSISTENCY_TEST=1 .venv\Scripts\python.exe -X utf8 scripts\check_source_consistency.py`  
整体结果：`WARN`，无 `FAIL`。

本报告只用于多源字段一致性、误差阈值和使用边界审计，不包含任何交易建议、候选股池、买卖点、仓位、策略信号、胜率或收益率预测。

## 测试范围

| 项目 | 值 |
|---|---|
| 股票代码 | `000001`, `600519` |
| 历史区间 | `2024-01-02` 到 `2024-12-31` |
| 指数对象 | 上证指数、深证成指、创业板指、沪深300 |
| 输出日志 | `logs/source_consistency_report.json` |
| 字段阈值 | 见 `FIELD_TOLERANCE_POLICY.md` |

## 总体裁决

| 检查项 | 结果 | 结论 |
|---|---:|---|
| `daily_kline` | WARN | Baostock 与 AKShare 日期、代码、OHLC、amount 对齐；volume 单位和 `pct_chg` 差异报警 |
| `trade_calendar` | PASS | Baostock 与 AKShare 交易日集合一致 |
| `full_realtime_quotes` | WARN | pytdx 主源与 easyquotation 备源字段齐全；单位、涨跌幅或 timestamp lag 报警 |
| `index_realtime` | WARN | pytdx 优先，easyquotation / AKShare fallback 字段齐全；单位或 timestamp lag 报警 |
| `full/lite` 边界 | PASS | adata 严格隔离在 lite，full 直接拒绝 |

任务013.1裁决：

```text
任务013.1：完成
是否允许独立项目正常使用：是
是否允许 S0 只读沙盒：是，但当前不接入
是否允许 S0 正式生产：否
```

## daily_kline

对比源：

```text
baostock daily_kline
akshare daily_kline
```

AKShare 当前实际接口：`stock_zh_a_hist` PASS，因此 daily_kline 当前使用 `akshare_hist`。`stock_zh_a_daily` 当前可用，仅作为低频 fallback。

结论：

- `date` 与 `code` 一致。
- `open/high/low/close` 未触发价格阈值 FAIL。
- `amount` 未触发金额阈值 FAIL。
- `volume` 记录单位比例 WARN。
- `pct_chg` 记录超阈值 WARN，需人工复核来源算法、复权/除权处理和四舍五入口径。

## trade_calendar

对比源：

```text
baostock trade_calendar
akshare tool_trade_date_hist_sina
```

结果：`PASS`

结论：Baostock 与 AKShare 交易日集合一致，满足盘后双源 gate。

## full_realtime_quotes

对比源：

```text
pytdx
easyquotation_sina
easyquotation_tencent
```

字段：

```text
code, name, last_price, open, high, low, pre_close, volume, amount, pct_chg
```

结果：`WARN`

结论：

- pytdx 主源返回 `000001`、`600519` 两行。
- easyquotation_sina / easyquotation_tencent 至少一个 backup PASS，实际两者均在 live smoke 中 PASS。
- full 必需字段齐全。
- WARN 来自跨源单位、`pct_chg` 或 timestamp lag，不自动修正、不覆盖源数据。

## index_realtime

对比源：

```text
pytdx
easyquotation_sina
easyquotation_tencent
akshare 指数 fallback
```

指数别名表：

| 指数 | 标准代码 | easyquotation 代码 | AKShare 代码 |
|---|---|---|---|
| 上证指数 | `000001` | `sh000001` | `000001` |
| 深证成指 | `399001` | `sz399001` | `399001` |
| 创业板指 | `399006` | `sz399006` | `399006` |
| 沪深300 | `000300` | `sh000300` | `000300` |

结果：`WARN`

结论：

- pytdx 返回 4 个目标指数并通过字段标准化。
- easyquotation_sina / easyquotation_tencent / AKShare 指数 fallback 均保留。
- WARN 来自 timestamp lag 或成交量单位比例差异。
- 若未来 pytdx 指数实时不可用，指数链路保留 fallback 组合，不把 AKShare 股票实时升级为主源。

## lite 边界

结果：`PASS`

结论：

- adata 仅进入 `lite_realtime_quotes`。
- adata 不在 `full_realtime_quotes` 默认策略中。
- adata 不在 `realtime_quotes` 默认策略中。
- `ADataAdapter.supported_features` 不暴露 `full_realtime_quotes` 或 `realtime_quotes`。
- 直接调用 adata full 方法返回 `UnsupportedFeatureError`。

## WARN 汇总

| 类型 | 对象 | 说明 |
|---|---|---|
| 单位差异 | daily volume | AKShare 与 Baostock 历史成交量存在单位口径差异 |
| 字段算法差异 | daily pct_chg | 两个测试股票均存在超阈值差异，需人工复核来源算法/复权口径 |
| 单位差异 | realtime/index volume | pytdx、easyquotation、AKShare 指数实时成交量存在比例差异 |
| timestamp lag | realtime/index | 不同公开源实时刷新时点不完全一致 |

## FAIL 汇总

无。

## 人工复核项

- `daily_kline.pct_chg` 的来源算法、复权/除权处理和四舍五入口径。
- pytdx 与网页源成交量单位口径的正式文档依据。
- 后续 S0 只读沙盒只能读取 full 字段来源，不得使用 adata lite 补 full 字段。
