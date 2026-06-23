# Source Policy V0.6 Decision

任务：任务013.1｜pytdx 实时主源切换与 AKShare 盘后优先级调整

生成日期：2026-06-12

## 最终裁决

- 任务013.1：完成。
- pytdx：进入 `realtime_quotes` / `full_realtime_quotes` 默认第一源。
- easyquotation：`easyquotation_sina`、`easyquotation_tencent` 继续作为实时 fallback。
- AKShare：调整为盘后优先源；不作为股票实时主源。
- Baostock：盘后 backup。
- adata：仍仅允许 `lite_realtime_quotes`，不得替代 full realtime。
- S0 只读沙盒：允许，但当前不接入。
- S0 正式生产：不允许。
- QMT / 券商账户 / 自动交易：仍禁止。

## V0.6 默认链路

```text
full_realtime_quotes:  pytdx -> easyquotation_sina -> easyquotation_tencent
realtime_quotes:       pytdx -> easyquotation_sina -> easyquotation_tencent
minute_kline:          pytdx
index_realtime:        pytdx -> easyquotation_sina -> easyquotation_tencent -> akshare
daily_kline:           akshare -> baostock
trade_calendar:        akshare -> baostock
lite_realtime_quotes:  adata
stock_basic:           baostock -> akshare
```

## live 验证摘要

- pytdx dependency：已安装，版本 `1.72`。
- TDX 可用服务器数量：1。
- TDX server pool：`primary_with_single_server_warning`。
- 可用服务器：`180.153.18.170:7709`。
- `get_security_quotes`：PASS。
- `realtime_quotes`：pytdx PASS。
- `full_realtime_quotes`：pytdx PASS。
- `index_realtime`：pytdx PASS，覆盖上证指数、深证成指、创业板指、沪深300。
- `minute_kline`：pytdx PASS。

## 字段标准化

pytdx realtime 已标准化到 full realtime 必需字段：

```text
code, name, last_price, pre_close, open, high, low, volume, amount,
pct_chg, source, source_latency_ms, source_status, data_timestamp
```

字段派生记录：

- `pct_chg`：由 pytdx `price` 与 `last_close` 计算。
- `name`：优先来自 pytdx `get_security_list`；常见指数使用内置指数别名补齐。
- `date`：pytdx quote 只有 `servertime`，日期使用本地自然日生成。
- `time`：来自 pytdx `servertime`。

字段警告：

- `volume` 保留 pytdx 原始 `vol`，跨源一致性可能出现单位差异报警。
- 本轮未做价格缩放修正，价格区间验证未发现需要缩放的问题。

## AKShare 盘后说明

- `stock_zh_a_hist` 当前 live PASS，因此 `daily_kline` 当前实际使用 `akshare_hist`。
- `stock_zh_a_daily` 当前也可用，但只作为 `akshare_stock_zh_a_daily_low_frequency` fallback。
- `trade_calendar` 使用 `akshare -> baostock`。
- AKShare 实时接口不作为股票实时主源，仅保留 optional 或指数 fallback。

## Gate

```text
post_close_gate=PASS
realtime_gate=PASS
index_realtime_gate=PASS
minute_gate=PASS
overall_live_gate=PASS
```

一致性校验：

- `overall_status=WARN`，无 FAIL。
- WARN 仅为跨源单位、涨跌幅差异或实时 timestamp lag 报警，不产生交易判断。

## 禁止事项

本项目仍不接入 S0 正式生产、QMT、券商账户、cookie/token/账号登录态，不提供荐股、候选股池、策略信号、买卖点、仓位、收益率承诺、胜率或自动交易逻辑。
