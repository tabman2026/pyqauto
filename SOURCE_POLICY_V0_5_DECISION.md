# SOURCE_POLICY_V0_5_DECISION

生成时间：2026-06-12

任务：012.2F｜按最新文档重测 AKShare / adata 调用方式

## 1. 默认 source policy

```text
daily_kline:           baostock -> akshare
trade_calendar:        baostock -> akshare
realtime_quotes:       easyquotation_sina -> easyquotation_tencent
full_realtime_quotes:  easyquotation_sina -> easyquotation_tencent
lite_realtime_quotes:  adata
index_realtime:        easyquotation_sina -> easyquotation_tencent -> akshare
minute_kline:          <no default source>
stock_basic:           baostock -> akshare
```

## 2. 恢复依据

| 功能 | 恢复源 | 依据 |
|---|---|---|
| `daily_kline` | AKShare | `stock_zh_a_daily` raw 非空；adapter 修复后 live gate PASS |
| `lite_realtime_quotes` | adata | 签名确认 `code_list` 返回轻量字段；lite gate PASS、full gate FAIL |
| `index_realtime` | AKShare | `stock_zh_index_spot_sina()` raw PASS；adapter fallback gate PASS |

## 3. 继续禁用

- AKShare `full_realtime_quotes`：`stock_zh_a_spot_em` 与分市场 spot 当前远端断开。
- AKShare `stock_zh_a_hist`：当前远端断开，不作为恢复依据。
- AKShare 指数 EM：当前远端断开，不作为恢复依据。
- adata `daily_kline`：`get_market()` 按文档示例仍返回空表。
- adata `full_realtime_quotes`：缺 `pre_close/open/high/low`。
- efinance、mootdx、Ashare：仍为 optional 或不可用，不进入默认链路。

## 4. live gate

| gate | 结果 |
|---|---:|
| `post_close_gate` | PASS |
| `realtime_gate` | PASS |
| `index_realtime_gate` | PASS |
| `overall_live_gate` | PASS |

## 5. 放行裁决

| 裁决项 | 结论 |
|---|---|
| 任务012.2F | 完成 |
| 是否允许进入任务013 | 是，但本轮不执行任务013 |
| 是否允许 S0 盘后只读沙盒 | 是 |
| 是否允许 S0 实时沙盒 | 是 |
| 是否允许 S0 正式生产 | 否 |

本轮未接入 S0，未接入 QMT 或券商账户，未输出任何交易建议。
