# LIVE_SMOKE_TEST_REPORT

生成时间：2026-06-12

数据来源：`logs/smoke_test_report.json`

## 1. Gate 结果

| gate | 结果 |
|---|---:|
| `live_enabled` | PASS |
| `post_close_gate` | PASS |
| `realtime_gate` | PASS |
| `index_realtime_gate` | PASS |
| `overall_live_gate` | PASS |

## 2. 通过源

| feature | PASS 源 |
|---|---|
| `daily_kline` | AKShare、Baostock |
| `trade_calendar` | AKShare、Baostock |
| `full_realtime_quotes` | easyquotation_sina、easyquotation_tencent |
| `lite_realtime_quotes` | adata |
| `index_realtime` | AKShare、easyquotation_sina、easyquotation_tencent |

## 3. 未通过或禁用

- AKShare `full_realtime_quotes`：spot 远端断开。
- adata `full_realtime_quotes`：缺 `pre_close/open/high/low`，只能 lite。
- adata `daily_kline`：空表。
- efinance、mootdx、Ashare：不进入默认链路。

## 4. 裁决

| 裁决项 | 结论 |
|---|---|
| 任务012.2F | 完成 |
| 是否允许进入任务013 | 是，但本轮未执行任务013 |
| 是否允许 S0 盘后只读沙盒 | 是 |
| 是否允许 S0 实时沙盒 | 是 |
| 是否允许 S0 正式生产 | 否 |

本轮未接入 S0、QMT、券商账户或自动交易，未输出任何交易建议。
