# TASK014C Gate - 2026-06-12

- [x] `PytdxAdapter` 运行时读取 `config/pytdx_servers_active.json`。
- [x] pytdx 运行时排序为 `primary -> hot_backup -> backup`，同级按 `latency_ms` 升序。
- [x] 仅使用 `connect_status=PASS` 且 `quote_status=PASS` 的服务器。
- [x] disabled 服务器被跳过。
- [x] primary 正常时优先使用 primary。
- [x] primary 失败时自动切换 hot backup。
- [x] primary + hot backup 失败时自动切换 backup pool。
- [x] pytdx 全部失败后，`realtime_quotes` / `full_realtime_quotes` / `index_realtime` fallback 到 easyquotation。
- [x] `minute_kline` 保持 pytdx-only，不新增 easyquotation minute fallback。
- [x] fallback trace 记录 `attempted_servers`、`selected_server`、`failover_reason`。
- [x] JSONL 审计写入 `logs/source_router.jsonl`。
- [x] SQLite 审计写入 `logs/source_router.db`。
- [x] 新增并写入 `pytdx_runtime_failover_trace`。
- [x] source policy 未修改。
- [x] easyquotation fallback 未删除。
- [x] 质量闸门、熔断、审计日志未删除。
- [x] full/lite 边界未破坏，adata 仍仅用于 `lite_realtime_quotes`。
- [x] `ENABLE_PYTDX_FAILOVER_TEST=1 scripts\debug_pytdx_runtime_failover.py` PASS。
- [x] `ENABLE_LIVE_SMOKE_TEST=1 scripts\smoke_test_live.py` PASS。
- [x] 允许继续 5 日稳定性观察。
- [x] 允许独立项目继续正常使用。
- [ ] S0 正式生产仍禁止。
- [x] 未接入 S0/QMT/券商账户，未输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。

# TASK016 Gate - 2026-06-12

- [x] 字段单位冻结完成：`volume=share`、`amount=yuan`、`pct_chg=percent`。
- [x] `config/field_unit_policy.json` 已生成。
- [x] `config/source_unit_policy.json` 已生成，任务013 WARN 字段未写成 high confidence。
- [x] `unit_normalizer` 保留 raw 字段、normalized 字段、conversion_factor、unit_confidence 和 `field_warnings`。
- [x] `source_switch_consistency` 覆盖 pytdx -> easyquotation_sina、easyquotation_sina -> easyquotation_tencent、akshare -> baostock、akshare_hist -> akshare_stock_zh_a_daily_low_frequency。
- [x] 单位一致性检查 `PASS`：`logs/unit_consistency_report.json`。
- [x] 切源一致性检查 `WARN`，无 BLOCK：`logs/source_switch_consistency_report.json`。
- [x] lite_realtime 仍严格隔离，未进入 full realtime。
- [x] source policy 未修改；fallback、熔断、审计日志未删除。
- [x] 不接入 S0/QMT/券商账户，不自动交易，不输出交易建议或交易计划。
- [x] 允许继续 5 日稳定性观察：是。
- [ ] 允许 S0 正式生产：否。

# PRODUCTION_CHECKLIST

生成时间：2026-06-12

## 任务014B Gate

- [x] V0.6 source policy 已冻结，本轮未修改默认链路。
- [x] 新增 `scripts/pytdx_server_pool_refresh.py`，默认不联网，必须 `ENABLE_PYTDX_SERVER_REFRESH=1`。
- [x] 候选服务器来源覆盖当前已验证服务器、pytdx `hq_hosts`、`config/pytdx_servers_extra.json`。
- [x] 所有可用服务器均经过 live probe，未测试服务器未标记为可用。
- [x] 输出 `logs/pytdx_server_pool_refresh.json`。
- [x] 输出 `config/pytdx_servers_active.json`。
- [x] pytdx PASS 服务器数量为 34，`server_pool_ready=True`。
- [x] `single_server_warning=False`。
- [x] easyquotation_sina / easyquotation_tencent 仍作为实时 fallback。
- [x] 0 个 PASS 时 pytdx fail-fast，并保留 easyquotation fallback。

## 自动稳定性观察 Gate

- [x] `scripts/run_stability_watch_windows.bat` 已完成，显式设置 `ENABLE_STABILITY_WATCH=1`。
- [x] `scripts/install_stability_watch_task_windows.bat` 已完成。
- [x] `scripts/uninstall_stability_watch_task_windows.bat` 已完成。
- [x] Windows 计划任务已安装：`A股行情源路由器_稳定性观察`。
- [x] 默认每天 15:40 运行。
- [x] 交易日过滤已实现；非交易日 SKIP，不计入 5 日观察。
- [x] `WinError 10013` / `PermissionError` / `Access is denied` 分类为 `local_network_permission_error`。
- [x] 同日重跑历史已保留在 `same_day_previous_runs`。
- [x] 每日输出 `logs/stability_daily_YYYYMMDD.json`。
- [x] 每日输出 `reports/STABILITY_DAILY_YYYYMMDD.md`。
- [x] 5 日汇总输出 `STABILITY_5DAY_SUMMARY.md`。
- [x] 最新稳定性观察 `daily_acceptance=PASS`。
- [x] 最新 5 日汇总 `IN_PROGRESS`，当前 1/5 个交易日。

## live smoke gate

- [x] `post_close_gate=PASS`
- [x] `realtime_gate=PASS`
- [x] `index_realtime_gate=PASS`
- [x] `minute_gate=PASS`
- [x] `overall_live_gate=PASS`
- [x] source consistency：WARN，无 FAIL

## 当前允许项

- [x] 允许独立项目正常使用。
- [x] 允许继续连续 5 个交易日稳定性观察。
- [ ] 5 日观察完成前不接入 S0 只读沙盒。
- [ ] 不允许 S0 正式生产。

## 必须保持的限制

- [x] 不接入 S0、QMT、券商账户、cookie、token 或任何登录态。
- [x] 不输出荐股、候选股池、买卖点、仓位、策略信号、收益率、胜率或自动交易逻辑。
- [x] 默认测试不联网；真实源 smoke、source consistency、pytdx refresh、stability watch 必须显式启用环境变量。
- [x] JSON / JSONL 使用 UTF-8 和 `ensure_ascii=False`。
- [x] Windows bat 保留 `chcp 65001 >nul`。
- [x] `lite_realtime_quotes` 不得替代 `full_realtime_quotes`。
- [x] 不用空表、缺字段、旧日期或异常 0 值强行判 PASS。
- [x] 不为通过校验而改写源原始数据。

## 当前风险

- 5 日稳定性观察仍未完成，当前仅 1/5 个交易日。
- `daily_kline.pct_chg` 在 Baostock 与 AKShare 间存在超阈值 WARN，需人工确认算法/复权口径。
- 历史成交量和指数实时成交量存在单位比例差异，已记录但未自动修正。
- S0 正式生产仍需后续生产准入和更长周期稳定性验证。
