# STABILITY WATCH PLAN

生成日期：2026-06-12

## 目标

任务014A用于冻结当前 V0.6 独立项目状态，并建立连续 5 个交易日稳定性观察机制。观察只验证行情源路由器稳定性，不接入 S0、QMT、券商账户或任何自动交易链路，不输出交易建议、候选股池、策略信号、买卖点、仓位、收益率或胜率。

## 冻结状态

```text
realtime_quotes:       pytdx -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes:  pytdx -> easyquotation_sina -> easyquotation_tencent
daily_kline:           akshare -> baostock
trade_calendar:        akshare -> baostock
lite_realtime_quotes:  adata
index_realtime:        pytdx -> easyquotation_sina -> easyquotation_tencent -> akshare
minute_kline:          pytdx
stock_basic:           baostock -> akshare
```

V0.6 source policy 本轮不修改。pytdx 为实时第一源，但当前单服务器状态不得宣传为高可用，必须保留 easyquotation fallback。AKShare 为盘后第一源，Baostock 为盘后 backup。adata 仅允许 lite，不得进入 full。

## 每日观察命令

Windows 运行前必须先切换 UTF-8 控制台，并显式启用稳定性观察：

```powershell
chcp 65001 | Out-Null
$env:ENABLE_STABILITY_WATCH="1"
.venv\Scripts\python.exe -X utf8 scripts\daily_stability_watch.py
```

默认不联网。未设置 `ENABLE_STABILITY_WATCH=1` 时脚本只写 SKIP 记录并返回非通过。

## 每日输出

```text
logs/stability_daily_YYYYMMDD.json
reports/STABILITY_DAILY_YYYYMMDD.md
logs/smoke_test_report.json
logs/source_consistency_report.json
```

每日观察覆盖：

- pytdx server pool 可用服务器数量、最快服务器、平均延迟、`single_server_warning`。
- pytdx realtime/full/index/minute 默认链路状态和 fallback trace。
- easyquotation_sina / easyquotation_tencent fallback 可用性。
- AKShare daily/trade_calendar 状态、`stock_zh_a_hist` 或低频 fallback 路径、RemoteDisconnected 记录。
- Baostock daily/trade_calendar backup 状态。
- adata lite 状态和 full 隔离边界。
- source consistency WARN/FAIL、成交量单位差异、`pct_chg` 超阈值、指数成交量单位差异。
- `source_router.jsonl`、`source_router.db`、fallback trace、failure event、health score 审计写入。

## 5 日汇总命令

```powershell
chcp 65001 | Out-Null
.venv\Scripts\python.exe -X utf8 scripts\stability_summary.py
```

汇总脚本只读取本地日报 JSON，不联网。输出：

```text
STABILITY_5DAY_SUMMARY.md
logs/stability_5day_summary.json
```

不足 5 个交易日报告时状态为 `IN_PROGRESS`。满 5 个交易日报告后，最近 5 日全部满足规则才输出 `PASS`。

## 通过标准

- 每日 `overall_live_gate=PASS`。
- pytdx 每日至少 1 个服务器可用；如果 5 日均只有 1 个服务器，必须保留 `single_server_warning`。
- easyquotation fallback 每日至少 1 个通道可用。
- AKShare daily_kline 每日至少一次成功；若失败，Baostock backup 必须成功。
- trade_calendar 双源每日可用。
- source consistency 无 FAIL。
- adata lite 未进入 full。
- 审计日志每日完整写入。
- 全程无 S0、QMT、券商、自动交易、交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划输出。

## 当前裁决

```text
是否接入 S0：否
是否接入 QMT：否
是否接入券商：否
是否允许 S0 正式生产：否
是否允许进入连续 5 个交易日稳定性观察：是
```
