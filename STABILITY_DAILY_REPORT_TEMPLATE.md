# STABILITY DAILY REPORT TEMPLATE

报告日期：YYYYMMDD

## 结论

```text
daily_acceptance:
overall_live_gate:
source_consistency:
是否允许计入 5 日观察:
是否允许 S0 正式生产: 否
```

## pytdx server pool

| 项目 | 结果 |
|---|---|
| 可用服务器数量 |  |
| 最快服务器 |  |
| 平均延迟 |  |
| 是否低于 2 个可用服务器 |  |
| 是否触发 single_server_warning |  |

## pytdx realtime

| 项目 | 结果 |
|---|---|
| 000001 realtime_quotes |  |
| 600519 realtime_quotes |  |
| index_realtime |  |
| minute_kline |  |
| 是否触发 fallback |  |

## easyquotation fallback

| 通道 | realtime | full | index | 可作为 fallback |
|---|---|---|---|---|
| easyquotation_sina |  |  |  |  |
| easyquotation_tencent |  |  |  |  |

## AKShare 盘后

| 项目 | 结果 |
|---|---|
| daily_kline |  |
| trade_calendar |  |
| 当前 daily 路径 |  |
| 是否 RemoteDisconnected |  |

## Baostock backup

| 项目 | 结果 |
|---|---|
| daily_kline |  |
| trade_calendar |  |

## adata lite

| 项目 | 结果 |
|---|---|
| lite_realtime_quotes |  |
| 是否严格隔离在 lite |  |
| 是否进入 full | 否 |

## source consistency WARN

| 项目 | 结果 |
|---|---|
| volume 100倍单位差异 |  |
| pct_chg 超阈值 |  |
| index volume 单位差异 |  |
| 是否出现新的 FAIL |  |

## 审计日志

| 项目 | 结果 |
|---|---|
| source_router.jsonl 写入 |  |
| source_router.db 写入 |  |
| fallback trace 完整 |  |
| failure event 完整 |  |
| health score 更新 |  |

## 禁止项确认

- 未接入 S0。
- 未接入 QMT。
- 未接入券商账户。
- 未启用自动交易。
- 未输出候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率。
- 本报告只用于行情源稳定性观察，不构成交易建议。
