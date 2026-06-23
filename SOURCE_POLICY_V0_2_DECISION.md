# SOURCE_POLICY_V0_2_DECISION

生成时间：2026-06-11

任务：任务012.2B｜AKShare 与 adata 最新接口专项重测

## 1. 裁决原则

本轮 source policy 只根据最新 raw debug 与 live smoke test 调整。旧 adapter 或旧 live smoke 失败不能直接证明 AKShare / adata 最新接口不可用；但最新 raw/live 未通过的接口也不能恢复默认链路。

未做事项：

- 不强行判 PASS。
- 不删除质量闸门、fallback、熔断或审计日志。
- 不接入 S0、QMT、券商账户、cookie、token 或自动交易。
- 不输出任何交易建议。

## 2. 最新证据

| 证据 | 结果 |
|---|---|
| AKShare 版本 | 1.18.64 |
| adata 版本 | 2.9.5 |
| AKShare `stock_zh_a_spot_em()` | FAIL，远端断开 |
| AKShare `stock_zh_index_spot_em()` | FAIL，最终重跑三个指定 `symbol` 均远端断开 |
| adata `get_market()` | FAIL，返回空表 |
| adata `list_market_current()` | 返回 2 行，但缺 `open/high/low`，标准映射 FAIL |
| live smoke test | 执行完成，`overall_live_gate=FAIL` |

## 3. 默认 source policy

当前可执行默认链路：

```text
daily_kline:     baostock
trade_calendar:  baostock -> akshare
realtime_quotes: easyquotation
index_realtime:  easyquotation
minute_kline:    <no default source>
stock_basic:     baostock -> akshare
```

## 4. 恢复 / 禁用裁决

| 功能 | 裁决 | 原因 |
|---|---|---|
| `daily_kline` | 不恢复 AKShare；不加入 adata | AKShare live FAIL；adata `get_market()` raw/live 空表 |
| `trade_calendar` | 保留 `baostock -> akshare` | live 中 Baostock、AKShare 均 PASS |
| `realtime_quotes` | 不恢复 AKShare；不加入 adata | AKShare raw/live FAIL；adata 有数据但缺必要字段 |
| `index_realtime` | 不恢复 AKShare；不加入 adata | AKShare raw/live FAIL；adata 无明确指数实时接口 |
| `stock_basic` | 保持 `baostock -> akshare` | 本轮未修改该链路 |

## 5. gate 裁决

| gate | 结果 |
|---|---:|
| `post_close_gate` | FAIL |
| `realtime_gate` | FAIL |
| `index_realtime_gate` | FAIL |
| `overall_live_gate` | FAIL |

最终裁决：任务012.2B完成但未通过；不允许进入任务013，不允许任何 S0 沙盒或正式生产。
