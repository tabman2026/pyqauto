# LIVE_SOURCE_POLICY_DECISION

生成时间：2026-06-12

任务：任务013.1｜pytdx 实时主源切换与 AKShare 盘后优先级调整

## 1. 策略裁决

pytdx 已通过专项 live 验证并进入实时默认第一源。AKShare 调整为盘后优先源，不再作为股票实时主源。easyquotation_sina / easyquotation_tencent 继续作为实时 fallback。Baostock 作为盘后 backup。adata 仍仅作为 `lite_realtime_quotes`。

| 功能 | 默认主源 | 默认备源 / fallback | 禁用或 optional |
|---|---|---|---|
| `daily_kline` | AKShare `stock_zh_a_hist` | Baostock；AKShare `stock_zh_a_daily` 低频 fallback | AKShare realtime 不参与 |
| `trade_calendar` | AKShare | Baostock | - |
| `realtime_quotes` | pytdx | easyquotation_sina -> easyquotation_tencent | AKShare 不作为股票实时主源 |
| `full_realtime_quotes` | pytdx | easyquotation_sina -> easyquotation_tencent | adata 禁止替代 full |
| `lite_realtime_quotes` | adata | 无 | 不得替代 full |
| `index_realtime` | pytdx | easyquotation_sina -> easyquotation_tencent -> AKShare 指数新浪 fallback | pytdx 指数异常时保留 fallback |
| `minute_kline` | pytdx | 无 | minute gate 当前非生产强阻断项 |
| `stock_basic` | Baostock | AKShare | 本轮未调整 |

## 2. 可执行 source policy

```text
daily_kline:           akshare -> baostock
trade_calendar:        akshare -> baostock
realtime_quotes:       pytdx -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes:  pytdx -> easyquotation_sina -> easyquotation_tencent
lite_realtime_quotes:  adata
index_realtime:        pytdx -> easyquotation_sina -> easyquotation_tencent -> akshare
minute_kline:          pytdx
stock_basic:           baostock -> akshare
```

## 3. live gate

最新 live 测试时间：`2026-06-12T07:05:41.985936+00:00`。

| gate | 规则 | 当前结果 | 结论 |
|---|---|---|---:|
| `post_close_gate` | `daily_kline` 至少 AKShare + Baostock 双源 PASS；`trade_calendar` 至少 AKShare + Baostock 双源 PASS | AKShare / Baostock 均 PASS | PASS |
| `realtime_gate` | pytdx PASS，且 easyquotation 至少 1 个 backup PASS | pytdx PASS；新浪/腾讯均 PASS | PASS |
| `index_realtime_gate` | pytdx 优先；若 pytdx 不支持则 fallback 组合可通过 | pytdx PASS；新浪/腾讯/AKShare fallback PASS | PASS |
| `minute_gate` | pytdx minute_kline PASS 则 PASS；否则非阻断 WARN | pytdx PASS | PASS |
| `overall_live_gate` | 盘后、实时、指数 gate 全部 PASS；minute 不阻断 | 已满足 | PASS |

## 4. 放行裁决

| 裁决项 | 结论 |
|---|---|
| 任务013.1 | 完成 |
| 独立项目正常使用 | 允许 |
| S0 只读沙盒 | 允许，但当前不接入 |
| S0 正式生产 | 禁止 |
| QMT / 券商 / 自动交易 | 禁止 |

本轮未接入 S0、QMT、券商账户或自动交易，未输出任何交易建议。
