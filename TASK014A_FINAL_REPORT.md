# 任务014A Final Report

生成日期：2026-06-12

任务名称：任务014A｜独立项目冻结与连续5个交易日稳定性观察

## 结论

```text
任务014A：完成
是否允许进入连续5个交易日稳定性观察：是
独立项目是否可继续正常使用：是
是否允许 S0 正式生产：否
```

本轮只冻结 V0.6 独立项目状态并建立稳定性观察机制，未接入 S0、QMT、券商账户或自动交易，未输出交易建议、候选股池、策略信号、买卖点、仓位、收益率或胜率。

## 新增内容

| 文件 | 作用 |
|---|---|
| `scripts/daily_stability_watch.py` | 每日稳定性观察，必须 `ENABLE_STABILITY_WATCH=1` 才联网 |
| `scripts/stability_summary.py` | 读取本地日报并生成 5 日汇总，不联网 |
| `STABILITY_WATCH_PLAN.md` | 观察计划 |
| `STABILITY_DAILY_REPORT_TEMPLATE.md` | 日报模板 |
| `STABILITY_OBSERVATION_RULES.md` | 观察通过/失败规则 |
| `TASK014A_FINAL_REPORT.md` | 本报告 |

## 冻结策略

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

V0.6 source policy 未修改。pytdx 是实时第一源，但当前仍只有 1 个 TDX 服务器可用，状态必须记录为 `primary_with_single_server_warning`，不得宣传为高可用。easyquotation 必须保留为实时 fallback。AKShare 是盘后第一源；Baostock 是盘后 backup。adata 仅 lite。

## 本日稳定性观察结果

| 项目 | 结果 |
|---|---:|
| daily_acceptance | PASS |
| overall_live_gate | PASS |
| pytdx 可用服务器数量 | 1 |
| pytdx server_pool_status | `primary_with_single_server_warning` |
| easyquotation fallback | PASS |
| AKShare daily_kline | PASS，当前路径 `akshare_hist` |
| Baostock backup | PASS |
| adata lite 边界 | PASS |
| source consistency | WARN，无 FAIL |
| 审计日志 | JSONL / SQLite / fallback trace / health score 均写入 |
| 5 日汇总 | IN_PROGRESS，当前 1/5 日 |

## 验收命令

| 命令 | 结果 |
|---|---:|
| `.venv\Scripts\python.exe -X utf8 -m pytest -q` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m compileall -q astock_source_router tests examples` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\smoke_test_offline.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\doctor_env.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m ruff check .` | PASS |
| `ENABLE_STABILITY_WATCH=1 scripts\daily_stability_watch.py` | PASS |
| `scripts\stability_summary.py` | PASS，`IN_PROGRESS` |

说明：首次稳定性观察在沙盒内因 `WinError 10013` 网络权限失败；按审批规则提升联网权限后重跑通过。

## 输出文件

```text
logs/stability_daily_20260612.json
reports/STABILITY_DAILY_20260612.md
logs/stability_5day_summary.json
STABILITY_5DAY_SUMMARY.md
```

## 必答项

| 问题 | 结论 |
|---|---|
| 任务014A是否完成 | 是 |
| 是否接入 S0 | 否 |
| 是否接入 QMT | 否 |
| 是否接入券商 | 否 |
| 是否输出交易建议 | 否 |
| 是否保持独立项目状态 | 是 |
| 是否冻结 V0.6 source policy | 是 |
| pytdx 是否为实时第一源 | 是 |
| AKShare 是否为盘后第一源 | 是 |
| easyquotation 是否为实时 fallback | 是 |
| Baostock 是否为盘后 fallback | 是 |
| adata 是否仅 lite | 是 |
| 是否生成 5 日稳定性观察机制 | 是 |
| 是否允许进入 5 日观察期 | 是 |
| 是否允许 S0 正式生产 | 否 |

## 审计结论

- 未接入 S0、QMT、券商账户、cookie、token 或登录态。
- 未输出候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率。
- 默认测试不联网；稳定性观察必须 `ENABLE_STABILITY_WATCH=1`。
- JSON / JSONL 输出继续使用 UTF-8 和 `ensure_ascii=False`。
- 未删除质量闸门、fallback、熔断或审计日志。
- S0 正式生产仍禁止。
