# SOURCE_POLICY_V0_3_DECISION

生成时间：2026-06-12

任务：任务012.2C｜备用源补测与 easyquotation 双通道拆分

## 1. 裁决摘要

本轮不再恢复 AKShare realtime 或 adata。`easyquotation` 已拆分为 `easyquotation_sina` 与 `easyquotation_tencent`，二者在专项测试和完整 live smoke 中均通过 `realtime_quotes` 与 `index_realtime` 质量闸门。

注意：新浪与腾讯通道仍同属 `easyquotation` Python 库，只代表同库不同底层源，不等价于完全独立库级双源。

## 2. 默认 source policy

```text
daily_kline:     baostock
trade_calendar:  baostock -> akshare
realtime_quotes: easyquotation_sina -> easyquotation_tencent
index_realtime:  easyquotation_sina -> easyquotation_tencent
minute_kline:    <no default source>
stock_basic:     baostock -> akshare
```

## 3. 未进入默认链路

| source | 功能 | 裁决 |
|---|---|---|
| efinance | `realtime_quotes` | 专项 live PASS，但完整 live smoke 同轮出现 RemoteDisconnected；仅 optional，不进默认链路 |
| efinance | `daily_kline` | FAIL，不进默认链路 |
| efinance | `index_realtime` | FAIL，不进默认链路 |
| Ashare | 全部 | 依赖不可安装 / 不可导入，SKIP |
| mootdx | `realtime_quotes`、`daily_kline` | raw 有数据但未通过标准 adapter 质量闸门，仅记录为 raw 探测 |
| mootdx | `minute_kline` | adapter 质量闸门 FAIL |
| pytdx | 全部 | 需要显式 TDX 服务器和市场配置，SKIP |
| AKShare | `daily_kline/realtime_quotes/index_realtime` | 继续禁用 |
| adata | `daily_kline/realtime_quotes/index_realtime` | 继续禁用 |

## 4. Gate 裁决

完整 live smoke：`logs/smoke_test_report.json`，时间 `2026-06-11T19:00:24.378058+00:00`。

| gate | 结果 | 依据 |
|---|---:|---|
| `post_close_gate` | FAIL | `daily_kline` 仅 Baostock PASS；`trade_calendar` Baostock 与 AKShare PASS |
| `realtime_gate` | PASS | primary `easyquotation_sina` PASS；backup `easyquotation_tencent` PASS |
| `index_realtime_gate` | PASS | primary `easyquotation_sina` PASS；backup `easyquotation_tencent` PASS |
| `overall_live_gate` | FAIL | `post_close_gate` 未通过 |

## 5. 放行裁决

| 裁决项 | 结论 |
|---|---|
| 任务012.2C | 完成但未达到整体门槛 |
| 进入任务013 | 否 |
| S0 盘后只读沙盒 | 否 |
| S0 实时沙盒 | 否 |
| S0 正式生产 | 否 |

下一步：继续补第二个盘后 `daily_kline` 真实源。
