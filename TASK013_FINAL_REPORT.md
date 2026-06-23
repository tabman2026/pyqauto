# TASK013_FINAL_REPORT

生成时间：2026-06-12

## 任务结论

任务013“多源字段一致性校验与使用边界冻结”已完成。离线回归通过；live 一致性校验整体为 `WARN`、无 `FAIL`；live smoke gate 复核为 `overall_live_gate=PASS`。

本轮未接入 S0、QMT、券商账户或自动交易；未输出任何交易建议、候选股池、买卖点、仓位、策略信号或收益率预测。

## 必答裁决

| # | 问题 | 结论 |
|---:|---|---|
| 1 | 任务013是否完成 | 完成 |
| 2 | baostock 与 akshare daily_kline 是否一致 | WARN：日期、代码、OHLC、amount 对齐；volume 存在单位比例；`pct_chg` 存在超阈值差异 |
| 3 | baostock 与 akshare trade_calendar 是否一致 | PASS：2024 区间交易日集合一致，均为 242 个交易日 |
| 4 | easyquotation_sina 与 easyquotation_tencent full_realtime_quotes 是否一致 | PASS：full 字段齐全，未发现超阈值差异 |
| 5 | easyquotation 与 akshare index_realtime 是否一致 | WARN：字段齐全、价格通过；成交量存在单位比例差异 |
| 6 | adata lite_realtime_quotes 是否被严格隔离 | PASS：仅 lite，full 直接 `UnsupportedFeatureError` |
| 7 | 是否发现字段单位差异 | 是：daily volume、index volume |
| 8 | 是否发现日期差异 | 未发现关键日期集合差异 |
| 9 | 是否发现价格差异 | 未发现超阈值价格差异 |
| 10 | 是否发现成交量 / 成交额差异 | 成交量存在单位比例 WARN；成交额未触发超阈值 WARN |
| 11 | 哪些差异为 WARN | daily volume 单位、daily `pct_chg`、index volume 单位 |
| 12 | 哪些差异为 FAIL | 无 |
| 13 | 是否允许进入任务014 | 是 |
| 14 | 是否允许 S0 只读沙盒接入 | 是 |
| 15 | 是否允许 S0 正式生产 | 否 |
| 16 | 仍需人工确认的问题 | `pct_chg` 算法/复权口径；指数成交量单位文档依据；S0 沙盒不得使用 lite 补 full |

## 验收命令

| 命令 | 结果 |
|---|---:|
| `.venv\Scripts\python.exe -X utf8 -m pytest -q` | PASS，30 passed，1 个既有 pandas FutureWarning |
| `.venv\Scripts\python.exe -X utf8 -m compileall -q astock_source_router tests examples` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\smoke_test_offline.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\doctor_env.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m ruff check .` | PASS |
| `ENABLE_SOURCE_CONSISTENCY_TEST=1 .venv\Scripts\python.exe -X utf8 scripts\check_source_consistency.py` | WARN，无 FAIL |
| `ENABLE_LIVE_SMOKE_TEST=1 .venv\Scripts\python.exe -X utf8 scripts\smoke_test_live.py` | PASS，`overall_live_gate=PASS` |

## 日志确认

| 文件 | 状态 |
|---|---:|
| `logs/source_consistency_report.json` | 存在 |
| `logs/smoke_test_report.json` | 存在 |
| `logs/source_router.jsonl` | 存在 |
| `logs/source_router.db` | 存在 |
| `logs/environment_report.json` | 存在 |

## 产物

- `scripts/check_source_consistency.py`
- `SOURCE_CONSISTENCY_REPORT.md`
- `FULL_LITE_REALTIME_USAGE_BOUNDARY.md`
- `FIELD_TOLERANCE_POLICY.md`
- `TASK013_FINAL_REPORT.md`
- `logs/source_consistency_report.json`

## 最终放行

```text
任务013：完成
是否允许进入任务014：是
是否允许 S0 只读沙盒接入：是
是否允许 S0 正式生产：否
```
