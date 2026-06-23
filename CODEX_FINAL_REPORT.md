# TASK014C UPDATE - 2026-06-12

任务014C已完成并通过：pytdx adapter 运行时会读取 `config/pytdx_servers_active.json`，按 `primary -> hot_backup -> backup` 排序，且同级按 `latency_ms` 升序选择服务器。运行时仅使用 `connect_status=PASS` 且 `quote_status=PASS` 的候选，跳过 disabled 服务器。

已验证 `realtime_quotes`、`full_realtime_quotes`、`index_realtime`、`minute_kline`：正常路径使用 primary `58.63.254.191:7709`；模拟 primary 失败自动切换 hot backup `183.60.224.177:7709`；模拟 primary + hot backup 失败自动切换 backup `119.29.19.242:7709`；模拟全部 pytdx 失败后，`realtime_quotes`、`full_realtime_quotes`、`index_realtime` fallback 到 `easyquotation_sina`。`minute_kline` 仍为 pytdx-only，全部 pytdx 失败时不新增 easyquotation minute fallback。

审计已增强：JSONL `logs/source_router.jsonl`、SQLite `logs/source_router.db` 均写入；新增 SQLite 表 `pytdx_runtime_failover_trace`；返回 metadata / fallback trace 记录 `pytdx_server_ip`、`pytdx_server_port`、`pytdx_server_role`、`pytdx_server_latency_ms`、`pytdx_failover_attempts`、`selected_server`、`failover_reason`。当前表内已有运行时记录。

验收结果：`pytest` PASS，`compileall` PASS，offline smoke PASS，doctor PASS，ruff PASS，`ENABLE_PYTDX_FAILOVER_TEST=1 scripts/debug_pytdx_runtime_failover.py` PASS，`ENABLE_LIVE_SMOKE_TEST=1 scripts/smoke_test_live.py` PASS。source policy 未修改，easyquotation fallback 未破坏，full/lite 边界未破坏，允许继续 5 日稳定性观察，独立项目允许继续正常使用，S0 正式生产仍为否。未接入 S0/QMT/券商账户，未输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。

# TASK016 UPDATE - 2026-06-12

任务016已完成：字段单位冻结完成，`config/source_unit_policy.json` 已生成，`volume` 标准单位为 `share`，`amount` 标准单位为 `yuan`，`pct_chg` 标准口径为 `percent`。`pytdx.pct_chg` 以及缺失源涨跌幅时由价格推导的字段均标记为 derived，并记录公式 `(close - pre_close) / pre_close * 100`。

单位一致性检查：`PASS`，输出 `logs/unit_consistency_report.json` 与 `FIELD_UNIT_FREEZE_REPORT.md`。切源一致性检查：`WARN`，无 BLOCK，输出 `logs/source_switch_consistency_report.json` 与 `SOURCE_SWITCH_CONSISTENCY_REPORT.md`。已校验路径：`pytdx -> easyquotation_sina` WARN、`easyquotation_sina -> easyquotation_tencent` WARN、`akshare -> baostock` PASS、`akshare_hist -> akshare_stock_zh_a_daily_low_frequency` WARN。

本轮未修改 source policy，未影响当前 5 日稳定性观察，`lite_realtime_quotes` 仍严格隔离，未接入 S0/QMT/券商账户，未自动交易，未输出任何交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。允许继续 5 日稳定性观察：是。独立项目可继续正常使用：是。是否允许 S0 正式生产：否。

# CODEX_FINAL_REPORT

生成时间：2026-06-12

## 任务结论

任务014B已完成：pytdx server pool 已扩容并生成 active pool；本地自动稳定性观察和 Windows 定时任务脚本已完成，定时任务已安装。

本轮未修改 V0.6 source policy，未接入 S0、QMT、券商账户、cookie、token 或自动交易逻辑；未输出交易建议、候选股池、买卖点、仓位、策略信号、胜率或收益率预测。

## 当前默认链路

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

## 014B 核心结果

| 检查项 | 结果 | 摘要 |
|---|---:|---|
| pytdx server pool refresh | PASS | `ENABLE_PYTDX_SERVER_REFRESH=1` 后 live probe |
| 候选服务器数量 | 103 | current verified + pytdx `hq_hosts` + extra config 去重 |
| PASS 服务器数量 | 34 | 全部经过 `get_security_quotes` live probe |
| primary server | PASS | `58.63.254.191:7709` |
| hot backup server | PASS | `183.60.224.177:7709` |
| `single_server_warning` | 解除 | False |
| `server_pool_ready` | PASS | True |
| active pool | PASS | `config/pytdx_servers_active.json` |
| 自动稳定性观察脚本 | PASS | `scripts/run_stability_watch_windows.bat` |
| Windows 定时任务脚本 | PASS | install/uninstall 均完成 |
| Windows 定时任务 | PASS | `A股行情源路由器_稳定性观察` 已安装，15:40 |
| 今日 daily_acceptance | PASS | 可计入 5 日观察 |
| 今日 overall_live_gate | PASS | live smoke gate 通过 |
| source consistency | WARN | WARN 31，无 FAIL |
| easyquotation fallback | PASS | 新浪和腾讯通道仍可作为 fallback |
| AKShare 盘后 | PASS | daily/calendar 可用；专项 daily endpoint fallback 可用 |
| Baostock backup | PASS | daily/calendar backup 可用 |
| adata lite 边界 | PASS | 仅 lite，full 直接拒绝 |
| 审计日志 | PASS | JSONL / SQLite / fallback trace / health score 均写入 |
| 5 日汇总 | IN_PROGRESS | 当前 1/5 个交易日 |

## 验收结果

| 命令 | 结果 |
|---|---:|
| `.venv\Scripts\python.exe -X utf8 -m pytest -q` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m compileall -q astock_source_router tests examples` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\smoke_test_offline.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\doctor_env.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m ruff check --no-cache .` | PASS |
| `ENABLE_PYTDX_SERVER_REFRESH=1 scripts\pytdx_server_pool_refresh.py` | PASS |
| `scripts\run_stability_watch_windows.bat` | PASS |
| `scripts\install_stability_watch_task_windows.bat` | PASS，任务已安装 |

稳定性观察前两次曾因 Baostock `trade_calendar` 20 秒源级超时失败；本轮没有出现 `WinError 10013`。提高稳定性观察内部 live source timeout 到 45 秒后重跑成功，失败记录保留在同日历史中。

## 决策

```text
任务014B：完成
是否允许继续5日稳定性观察：是
独立项目是否可继续正常使用：是
是否允许 S0 只读沙盒：当前不接入，等待 5 日观察结果
是否允许 S0 正式生产：否
QMT / 券商 / 自动交易：仍禁止
```

## 关键文件

- `scripts/pytdx_server_pool_refresh.py`
- `config/pytdx_servers_extra.json`
- `config/pytdx_servers_active.json`
- `config/stability_watch_schedule.json`
- `scripts/run_stability_watch_windows.bat`
- `scripts/install_stability_watch_task_windows.bat`
- `scripts/uninstall_stability_watch_task_windows.bat`
- `PYTDX_SERVER_POOL_EXPANSION_REPORT.md`
- `AUTO_STABILITY_WATCH_REPORT.md`
- `TASK014B_FINAL_REPORT.md`
- `logs/pytdx_server_pool_refresh.json`
- `logs/stability_daily_20260612.json`
- `reports/STABILITY_DAILY_20260612.md`
- `STABILITY_5DAY_SUMMARY.md`

## 人工复核项

- 当前 pytdx pool 已达到 `server_pool_ready`，但仍需连续 5 个交易日观察，不能据此直接进入 S0 正式生产。
- source consistency 为 WARN，无 FAIL；WARN 主要来自跨源单位差异、`pct_chg` 或 timestamp lag。
- 当前只有 1 个交易日观察通过，5 日稳定性结论尚未形成。
