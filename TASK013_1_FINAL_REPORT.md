# 任务013.1 Final Report

任务名称：任务013.1｜pytdx 实时主源切换与 AKShare 盘后优先级调整

生成日期：2026-06-12

## 结论

任务013.1：完成。

pytdx live PASS，且至少 1 个 TDX 服务器可用。因此本轮裁决为：

```text
pytdx：实时默认第一源
easyquotation：实时备用源
AKShare：盘后优先源
是否允许独立项目正常使用：是
是否允许 S0 只读沙盒：是，但当前不接入
是否允许 S0 正式生产：否
```

## 必答项

| 项目 | 结论 |
| --- | --- |
| pytdx 是否安装 | 是，`1.72` |
| pytdx 服务器池是否可用 | 是 |
| 可用 TDX 服务器数量 | 1 |
| server pool 状态 | `primary_with_single_server_warning` |
| pytdx realtime_quotes | PASS |
| pytdx full_realtime_quotes | PASS |
| pytdx minute_kline | PASS |
| pytdx 是否进入实时默认第一源 | 是 |
| easyquotation 是否仍为实时 backup | 是，`easyquotation_sina -> easyquotation_tencent` |
| AKShare 是否盘后优先 | 是 |
| AKShare daily_kline 当前接口 | `akshare_hist`，即 `stock_zh_a_hist` |
| Baostock 是否盘后 backup | 是 |
| adata 是否仍只作为 lite | 是 |
| post_close_gate | PASS |
| realtime_gate | PASS |
| index_realtime_gate | PASS |
| minute_gate | PASS |
| overall_live_gate | PASS |
| 是否允许独立项目正常使用 | 是 |
| 是否允许 S0 只读沙盒 | 是，但当前不接入 |
| 是否允许 S0 正式生产 | 否 |
| QMT / 券商 / 自动交易 | 仍禁止 |

## 验证摘要

- `scripts/debug_pytdx_server_pool.py`：PASS；`180.153.18.170:7709` 可连接并可返回测试行情。
- `scripts/debug_pytdx_realtime.py`：PASS；`000001`、`600519`、上证指数、深证成指、创业板指、沪深300 均完成标准化。
- `scripts/smoke_test_live.py`：`overall_live_gate=PASS`。
- `scripts/check_source_consistency.py`：`overall_status=WARN`，无 FAIL。

## 审计结论

- 未接入 S0、QMT、券商账户或自动交易。
- 未内置 cookie、token、账号或券商登录态。
- 未输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。
- JSON / JSONL 输出继续使用 UTF-8 与 `ensure_ascii=False`。
