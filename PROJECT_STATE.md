# TASK033.1 UPDATE - 2026-06-23

Task033.1 release target is `pyqauto` version `1.0.0rc2` as a prerelease
candidate. This task must not publish final `1.0.0`.

RC2 scope:

- Restore the frozen `pyqauto kline` CLI command.
- Restore `pytdx>=1.72` as a core dependency according to the `0.3.1` public
  install contract and V1 K-line freeze.
- Split GitHub Actions CI into minimal install and full dependency validation.
- Gate PyPI Trusted Publishing behind test, build, `twine check`, and
  distribution content scan jobs in the publish workflow.
- Add CLI command snapshot, help-without-network, installed wheel CLI, pytdx
  import boundary, and publish workflow gating tests.

Audit conclusion:

- `1.0.0rc1` remains preserved and is not overwritten.
- V1 Python API, field meanings, default source policy, fallback ordering, and
  audit log structure are unchanged.
- No new data source, adapter, architecture layer, trading system, strategy,
  prediction, stock-picking, broker, QMT, account, or automated trading behavior
  is introduced.
- RC2 remains a prerelease candidate only.

# TASK033 UPDATE - 2026-06-23

Task033 release target is `pyqauto` version `1.0.0rc1` as a prerelease
candidate. This task must not publish final `1.0.0`.

The V1 public API freeze candidate, Adapter Contract V1, Runtime Governance,
Reliability Graph, Autonomous Control Layer, Meta Control Plane, Stability
Layer, cross-layer integration tests, clean wheel installation validation, and
release checks are the release scope for this candidate.

Release governance:

- PyPI version: `1.0.0rc1`
- Git tag: `v1.0.0rc1`
- Current stable recommendation remains `pyqauto==0.3.1`
- `1.0.0rc1` is for RC testing only and is not the default recommendation for all users
- Development Status remains prerelease/Beta, not Production/Stable
- No default source policy change
- No field meaning change
- No audit log structure change
- No trading, strategy, prediction, stock-picking, broker, QMT, account, or automated trading behavior

# TASK030 UPDATE - 2026-06-22

Task030 completed: pyqauto v1 freeze documentation, router API wrappers,
adapter contract v1 defaults, release checks, and freeze tests are in place.
The frozen API scope is `meta_decision()`, `meta_explain()`, `source_health()`,
`kline()`, `realtime_quotes()`, and `diagnose()`.

The `fake` offline test adapter now has explicit unit assumptions in
`config/source_unit_policy.json` for deterministic contract tests. This does
not add a real data source, does not change executable default source policy,
and does not change audit log structure.

Acceptance results: `python -X utf8 -m pytest -q` PASS,
`python -X utf8 -m ruff check .` PASS,
`python -X utf8 scripts/check_release.py` PASS,
`python -X utf8 scripts/smoke_test.py` PASS, and
`python -X utf8 -m build` PASS after UTF-8 environment and isolated build
dependency network permission. Full results are recorded in
`TASK030_FINAL_REPORT.md`.

# TASK029 UPDATE - 2026-06-22

Task029 completed: added `pyqauto.meta` Meta Control Plane as the read-only
system brain for Governance, Reliability Graph, and Autonomy signals. The new
layer exposes `meta_decision()`, `meta_state()`, `meta_explain()`, and
`system_brain()`.

Audit conclusion: no source policy change, no field standard change, no audit
log schema change, no new real data source, no trading system, no strategy or
prediction, no investment advice, no QMT, no broker integration, and no
auto-trading behavior.

# TASK028 UPDATE - 2026-06-22

任务028已完成：新增 L6 Autonomous Control Layer，用于本地行情源路由的
自动恢复、异常识别、分数衰减和 schema drift 自愈。新增
`astock_source_router/autonomy/` 与 `pyqauto/autonomy/` 兼容命名空间，并在
`MarketRouter` 暴露 `autonomy_status()`、`recovery_state()`、
`anomaly_report()`、`source_weight_decay()`。

本任务未修改默认 source policy，未改变字段标准，未改变审计日志结构，未新增
真实数据源，未引入交易系统、策略/预测、投资建议、QMT、券商或自动交易。
审计结论：L6 仅作为 self-healing / self-recovery / self-stabilizing data
infrastructure，不用于选股或收益预测。

# TASK023 UPDATE - 2026-06-21

任务023已完成：新增 `python main.py --task source_schema_probe_live`，
用于真实联网探测 AkShare `stock_zh_a_spot_em`、pytdx quote、pytdx kline、
`easyquotation_sina`、`easyquotation_tencent` 的当前 raw schema、dtype、
样本行、标准字段映射、单位规则和 `validate_standard_output` 结果。

新增输出：`reports/latest/source_schema_probe_live.json` 和
`logs/source_schema_probe_live.jsonl`，均使用 UTF-8 和 `ensure_ascii=False`。
`diagnose` 会展示最新 live schema probe 摘要、漂移字段和拒绝原因。

schema drift 防火墙已建立：核心字段缺失或原始字段名漂移时标记
`schema_drift` / `field_missing`，不静默补 0，不返回未通过校验的 public
records。AkShare `成交量` 仍按“手”转换为 `volume_shares`，`成交额` 保持
`amount_yuan`，不除以 100。ETF / 北交所可选样本不支持时记录
`unsupported`，不误记为 failed。

验收结果：`python -X utf8 -m pytest` 通过（66 passed），
`python -X utf8 -m ruff check .` 通过。本任务未新增交易功能，未生成候选股池、
买卖信号、收益率、胜率，未接入 QMT、真实交易或自动交易。

# TASK014C UPDATE - 2026-06-12

当前状态：任务014C已完成。pytdx 运行时自动切换已验证通过，`PytdxAdapter` 会读取 `config/pytdx_servers_active.json`，按 `primary -> hot_backup -> backup` 和 `latency_ms` 使用服务器。当前 active pool 候选数为 34；primary 为 `58.63.254.191:7709`，hot backup 为 `183.60.224.177:7709`，最快 backup 为 `119.29.19.242:7709`。

运行时 failover 结论：primary 正常时优先使用 primary；primary 失败时切 hot backup；primary + hot backup 失败时切 backup；pytdx 全部失败后，`realtime_quotes`、`full_realtime_quotes`、`index_realtime` 由 source router fallback 到 `easyquotation_sina -> easyquotation_tencent`。`minute_kline` 仍为 pytdx-only，不新增 easyquotation minute fallback。

审计状态：`logs/source_router.jsonl`、`logs/source_router.db`、`logs/pytdx_runtime_failover_report.json` 均存在；SQLite 已新增并写入 `pytdx_runtime_failover_trace`。source policy 未修改，easyquotation fallback 未删除，熔断、质量闸门和审计日志保留，full/lite 边界保留。

放行状态：允许继续 5 日稳定性观察；允许独立项目继续正常使用；S0 正式生产仍禁止。当前不接入 S0、QMT、券商账户，不输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。

# TASK016 UPDATE - 2026-06-12

任务016已完成字段单位与切源一致性冻结：新增 `field_unit_policy.json`、`source_unit_policy.json`、单位 normalizer、切源一致性检查和对应测试。当前 source policy 未修改；`volume=share`、`amount=yuan`、`pct_chg=percent` 已冻结。单位一致性 `PASS`，切源一致性 `WARN` 且无 BLOCK。5 日稳定性观察可继续，S0 正式生产仍禁止。

# PROJECT_STATE

生成时间：2026-06-12

当前状态：任务014B已完成。项目继续冻结在“pytdx 实时优先、AKShare 盘后优先”的 V0.6 source policy；pytdx server pool 已扩容到 34 个 live PASS 服务器，状态为 `server_pool_ready`。自动稳定性观察已支持交易日过滤、同日重跑记录和 Windows 定时任务。

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

## 最新 pytdx server pool

| 项目 | 状态 |
|---|---:|
| 候选服务器 | 103 |
| PASS 服务器 | 34 |
| primary | `58.63.254.191:7709` |
| hot backup | `183.60.224.177:7709` |
| 原验证服务器 | `180.153.18.170:7709`，仍 PASS，当前为 backup |
| `single_server_warning` | False |
| `server_pool_ready` | True |
| active config | `config/pytdx_servers_active.json` |

## 最新稳定性观察

| 项目 | 状态 |
|---|---:|
| 观察日期 | 2026-06-12 |
| 交易日过滤 | PASS，计入 5 日观察 |
| `daily_acceptance` | PASS |
| `overall_live_gate` | PASS |
| `source_consistency` | WARN，无 FAIL |
| easyquotation fallback | PASS |
| AKShare daily/calendar | PASS / PASS |
| Baostock daily/calendar | PASS / PASS |
| adata lite 边界 | PASS |
| 审计日志 | PASS |
| 5 日汇总 | `IN_PROGRESS`，当前 1/5 个交易日 |

## 自动观察

| 项目 | 状态 |
|---|---|
| runner | `scripts/run_stability_watch_windows.bat` |
| 安装脚本 | `scripts/install_stability_watch_task_windows.bat` |
| 卸载脚本 | `scripts/uninstall_stability_watch_task_windows.bat` |
| Windows 计划任务 | 已安装 |
| 任务名 | `A股行情源路由器_稳定性观察` |
| 默认时间 | 15:40 |

## 放行状态

| 项目 | 状态 |
|---|---|
| 独立项目正常使用 | 允许 |
| 连续 5 个交易日稳定性观察 | 允许继续 |
| S0 只读沙盒 | 当前不接入；需等待 5 日观察结果 |
| S0 正式生产 | 禁止 |
| QMT / 券商 / 自动交易 | 禁止 |

## 仍需人工确认

- 当前仅完成 1/5 个交易日观察，不能形成 5 日稳定性通过结论。
- `daily_kline.pct_chg` 的算法、复权/除权处理和四舍五入口径。
- 指数实时成交量各源单位口径的正式文档依据。
- 即使 pytdx pool 已达到 `server_pool_ready`，也不得宣称 S0 正式生产可用。

本项目仍只作为本地行情源路由与适配框架，不提供数据再分发服务、投资建议或自动交易逻辑。
