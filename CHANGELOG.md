# 1.0.0rc1 - 2026-06-23

Release candidate only. This is not the final 1.0.0 release.

### Added

- V1 public API freeze candidate for the formal `pyqauto` namespace.
- Adapter Contract V1 and field standardization contract tests.
- Runtime Governance, Reliability Graph, Autonomous Control Layer, Meta Control Plane, and Stability Layer.
- Cross-layer integration coverage, stability restart semantics tests, and clean wheel installation validation.
- RC testing guide and release notes for PyPI prerelease validation.

### Audit

- Version target is exactly `1.0.0rc1`; the Git tag target is `v1.0.0rc1`.
- Development Status remains a prerelease Beta classifier, not Production/Stable.
- Default source policy, field meanings, audit log structure, and public API semantics remain frozen.
- The project remains market-data infrastructure only. It does not provide investment advice, trading execution, strategy signals, broker integration, QMT integration, or automated trading logic.

# TASK014C - 2026-06-12

### Added

- 新增 `scripts/debug_pytdx_runtime_failover.py`，默认不联网，必须显式设置 `ENABLE_PYTDX_FAILOVER_TEST=1` 才执行 live failover 验证。
- 新增 `tests/test_pytdx_runtime_failover.py`，使用 fake pytdx client 离线覆盖 active pool 加载、role/latency 排序、disabled 跳过、primary/hot_backup/backup 切换、全部失败异常、router fallback、fallback trace、metadata、source policy 和 full/lite 边界。
- 新增 `PYTDX_RUNTIME_FAILOVER_REPORT.md`、`PYTDX_RUNTIME_FAILOVER_DECISION.md`、`TASK014C_FINAL_REPORT.md`。
- SQLite 新增 `pytdx_runtime_failover_trace` 表。

### Changed

- `PytdxAdapter` 由“连接到第一台可用服务器后直接请求”增强为“每次请求按 active pool 逐服务器尝试并验证结果”。
- active pool 运行时候选仅保留 `connect_status=PASS` 且 `quote_status=PASS` 且非 disabled 的服务器。
- pytdx 运行时排序为 `primary -> hot_backup -> backup`，同级按 `latency_ms` 升序。
- pytdx 请求遇到连接失败、连接超时、请求超时、空数据、字段缺失、非法字段值、disabled 或未知异常时，自动尝试下一台服务器。
- `MarketRouter` 保留原 fallback 逻辑，并将 pytdx runtime failover metadata 写入 result metadata、fallback trace、JSONL 和 SQLite。
- `PytdxAllServersFailed` 错误消息改为摘要，完整 attempts 仍保留在异常属性和审计 metadata 中。
- 已知指数名称在 pytdx name lookup 前预填缓存，避免指数实时请求无意义扫描证券列表。

### Audit

- live failover：normal primary、primary fake fail、primary + hot fake fail、all pytdx fake fail 均通过。
- `realtime_quotes`、`full_realtime_quotes`、`index_realtime`、`minute_kline` 均通过 primary/hot_backup/backup runtime failover 验证。
- pytdx 全部失败后，`realtime_quotes`、`full_realtime_quotes`、`index_realtime` fallback 到 `easyquotation_sina`。
- `minute_kline` 保持 pytdx-only；全部 pytdx 失败后不新增 easyquotation minute fallback。
- 离线回归通过：pytest、compileall、offline smoke、doctor_env、ruff。
- live smoke 通过：`overall_live_gate=PASS`。
- source policy 未修改，easyquotation fallback 未破坏，full/lite 边界未破坏。
- 未接入 S0/QMT/券商账户，未输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。

# TASK016 - 2026-06-12

### Added

- 新增 `astock_source_router/core/unit_policy.py`、`unit_normalizer.py`、`source_switch_consistency.py`。
- 新增 `config/field_unit_policy.json`、`config/source_unit_policy.json`。
- 新增 `scripts/check_unit_consistency.py`、`scripts/check_source_switch_consistency.py`。
- 新增字段单位、源单位、切源一致性和 lite/full 边界测试。
- 新增 `FIELD_UNIT_POLICY.md`、`SOURCE_UNIT_POLICY.md`、`FIELD_UNIT_FREEZE_REPORT.md`、`SOURCE_SWITCH_CONSISTENCY_REPORT.md`、`TASK016_FINAL_REPORT.md`。

### Audit

- 字段单位检查：`PASS`。
- 切源一致性检查：`WARN`，无 BLOCK。
- 未修改 source policy，未新增数据源，未接入 S0/QMT/券商账户，未输出交易建议或自动交易逻辑。

# CHANGELOG

## 0.1.11 - 2026-06-12

### Added

- 新增 `scripts/pytdx_server_pool_refresh.py`，显式 `ENABLE_PYTDX_SERVER_REFRESH=1` 后探测 pytdx server pool。
- 新增 `config/pytdx_servers_extra.json` 与 `config/pytdx_servers_active.json`，记录手工候选和 live 排序后的 active pool。
- 新增 `config/stability_watch_schedule.json`。
- 新增 Windows 自动观察脚本：`scripts/run_stability_watch_windows.bat`、`scripts/install_stability_watch_task_windows.bat`、`scripts/uninstall_stability_watch_task_windows.bat`。
- 新增 `PYTDX_SERVER_POOL_EXPANSION_REPORT.md`、`AUTO_STABILITY_WATCH_REPORT.md`、`TASK014B_FINAL_REPORT.md`。

### Changed

- `PytdxAdapter` 默认优先读取 `config/pytdx_servers_active.json` 中 live PASS 且非 disabled 的服务器；若 active config 存在但无 PASS，则 pytdx fail-fast 并由路由 fallback 到 easyquotation。
- `scripts/daily_stability_watch.py` 升级为 `task014B_v1`，新增交易日过滤、调度触发记录、同日重跑历史和 `local_network_permission_error` 分类。
- `scripts/stability_summary.py` 改为只统计 `counted_in_5day=true` 的交易日 PASS 观察。
- 稳定性观察内部 live source timeout 调整为 45 秒，以保留质量闸门同时容纳 Baostock calendar 慢响应。

### Audit

- pytdx server pool refresh：候选 103 个，PASS 34 个，`server_pool_ready=True`。
- primary server：`58.63.254.191:7709`；hot backup：`183.60.224.177:7709`。
- 原已验证服务器 `180.153.18.170:7709` 仍 PASS，当前为 backup。
- 最新稳定性观察：`daily_acceptance=PASS`、`overall_live_gate=PASS`、source consistency `WARN` 无 FAIL，计入 5 日观察。
- Windows 计划任务 `A股行情源路由器_稳定性观察` 已安装，默认每天 15:40。
- 离线回归通过：pytest、compileall、offline smoke、doctor_env、ruff。
- 本轮不接入 S0、QMT、券商账户或自动交易，不输出交易建议、候选股池、策略信号、买卖点、仓位、收益率或胜率。
- S0 正式生产仍禁止。

## 0.1.10 - 2026-06-12

### Added

- 新增 `scripts/daily_stability_watch.py`，用于显式启用的每日稳定性观察。
- 新增 `scripts/stability_summary.py`，用于读取本地日报并生成 5 日稳定性汇总。
- 新增 `STABILITY_WATCH_PLAN.md`、`STABILITY_DAILY_REPORT_TEMPLATE.md`、`STABILITY_OBSERVATION_RULES.md`、`TASK014A_FINAL_REPORT.md`。

### Changed

- README、PROJECT_STATE、PRODUCTION_CHECKLIST、CODEX_FINAL_REPORT 更新为任务014A状态。
- V0.6 source policy 保持冻结：pytdx 实时优先、AKShare 盘后优先、easyquotation 与 Baostock 保留 fallback、adata 仅 lite。

### Audit

- 稳定性观察默认不联网，必须 `ENABLE_STABILITY_WATCH=1`。
- 每日输出 `logs/stability_daily_YYYYMMDD.json` 和 `reports/STABILITY_DAILY_YYYYMMDD.md`。
- 5 日汇总输出 `STABILITY_5DAY_SUMMARY.md` 和 `logs/stability_5day_summary.json`。
- 离线回归通过：pytest、compileall、offline smoke、doctor_env、ruff。
- 首日稳定性观察通过：`daily_acceptance=PASS`、`overall_live_gate=PASS`。
- 5 日汇总当前 `IN_PROGRESS`，已有 1 个日报。
- 本轮不接入 S0、QMT、券商账户或自动交易，不输出交易建议、候选股池、策略信号、买卖点、仓位、收益率或胜率。
- S0 正式生产仍禁止。

## 0.1.9 - 2026-06-12

### Added

- 新增 `astock_source_router/adapters/pytdx_adapter.py`，支持 `realtime_quotes`、`full_realtime_quotes`、`index_realtime`、`minute_kline`。
- 新增 `scripts/debug_pytdx_server_pool.py` 与 `PYTDX_SERVER_POOL_REPORT.md`，显式 live 验证 TDX 服务器池。
- 新增 `scripts/debug_pytdx_realtime.py` 与 `PYTDX_REALTIME_PRIMARY_REPORT.md`，验证 pytdx `get_security_quotes`、字段标准化、指数实时和分钟 K。
- 新增 `SOURCE_POLICY_V0_6_DECISION.md`、`TASK013_1_FINAL_REPORT.md`。
- 新增 `tests/test_pytdx_adapter.py`，离线锁定 pytdx 字段标准化与缺字段不伪造行为。

### Changed

- `DEFAULT_SOURCE_POLICY` 调整为 `realtime_quotes/full_realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent`。
- `index_realtime` 调整为 `pytdx -> easyquotation_sina -> easyquotation_tencent -> akshare`。
- `minute_kline` 默认源调整为 pytdx。
- `daily_kline/trade_calendar` 调整为 `akshare -> baostock`，AKShare 盘后优先，Baostock backup。
- AKShare 不再作为股票实时主源；AKShare 实时仅保留 optional 或指数 fallback。
- `scripts/smoke_test_live.py` 新增 `realtime_quotes` 与 `minute_gate`，并将实时 gate 改为 pytdx 主源 + easyquotation backup。
- source consistency 改为 pytdx 主源对 easyquotation 备源做 full realtime 一致性校验。
- MarketRouter 候选执行顺序改为严格遵循 source policy；熔断打开仍跳过，质量失败仍 fallback。

### Audit

- pytdx 1.72 已安装。
- pytdx server pool：1 个可用服务器，`primary_with_single_server_warning`，必须保留 easyquotation fallback。
- pytdx `get_security_quotes` PASS。
- pytdx `realtime_quotes/full_realtime_quotes/index_realtime/minute_kline` PASS。
- AKShare `stock_zh_a_hist` 当前 PASS，因此 `daily_kline` 当前使用 `akshare_hist`；`stock_zh_a_daily` 仅作为低频 fallback。
- live smoke gate：`post_close_gate=PASS`、`realtime_gate=PASS`、`index_realtime_gate=PASS`、`minute_gate=PASS`、`overall_live_gate=PASS`。
- source consistency：`overall_status=WARN`，无 FAIL。
- 任务013.1完成；允许独立项目正常使用；允许 S0 只读沙盒但当前不接入；S0 正式生产仍禁止。
- QMT、券商账户、自动交易、交易建议、候选股池、策略信号、仓位和收益率承诺仍禁止。

## 0.1.8 - 2026-06-12

### Added

- 新增 `scripts/check_source_consistency.py`，默认不联网，仅在 `ENABLE_SOURCE_CONSISTENCY_TEST=1` 或 `ENABLE_LIVE_SMOKE_TEST=1` 时访问真实源。
- 新增 `SOURCE_CONSISTENCY_REPORT.md`、`FULL_LITE_REALTIME_USAGE_BOUNDARY.md`、`FIELD_TOLERANCE_POLICY.md`、`TASK013_FINAL_REPORT.md`。
- 新增 `tests/test_adata_usage_boundary.py`，离线锁定 adata 不得暴露 full/realtime 能力。

### Changed

- `ADataAdapter` 对外能力收窄为 lite-only realtime：不再声明 `realtime_quotes` / `full_realtime_quotes`，直接调用 full 方法返回 `UnsupportedFeatureError`。
- `scripts/smoke_test_live.py` 中 adata 的关键 live 能力调整为 `lite_realtime_quotes`，避免把已禁用的 full 角色作为 adata 关键能力。
- 更新 README、CODEX_FINAL_REPORT、PRODUCTION_CHECKLIST、PROJECT_STATE，记录任务013结论。

### Audit

- 离线回归通过：pytest、compileall、offline smoke、doctor_env、ruff。
- live 一致性校验结果：整体 `WARN`，无 `FAIL`。
- `daily_kline` WARN：AKShare 与 baostock 历史成交量存在 `100` 倍单位比例；`pct_chg` 存在超阈值差异。
- `trade_calendar` PASS：2024 区间交易日集合一致。
- `full_realtime_quotes` PASS：easyquotation 新浪/腾讯字段齐全且未触发超阈值差异。
- `index_realtime` WARN：指数成交量存在源间单位比例差异。
- adata full/lite 边界 PASS：adata 仅进入 lite，full 直接拒绝。
- live smoke gate：`overall_live_gate=PASS`。
- 任务013完成；允许进入任务014；允许 S0 只读沙盒；S0 正式生产仍禁止。

## 0.1.7 - 2026-06-12

### Added

- 新增 `scripts/debug_latest_doc_calling.py`，按最新文档重测 AKShare / adata 原始接口，并写入 `logs/latest_doc_calling_report.json` 与 `LATEST_DOC_CALLING_REPORT.md`。
- 新增 `AKSHARE_ADATA_CALLING_FIX_REPORT.md`、`REALTIME_SCHEMA_SPLIT_DECISION.md`、`SOURCE_POLICY_V0_5_DECISION.md`。
- 新增 `full_realtime_quotes` 与 `lite_realtime_quotes` 两级质量闸门。

### Changed

- AKShare adapter 修复 `stock_zh_a_daily` 备用接口：使用 `sh/sz` 前缀、映射 `turnover`、向前取缓冲数据推导前收/涨跌幅，并过滤回目标日期。
- AKShare 指数实时在 EM 不可用时尝试 `stock_zh_index_spot_sina()` fallback。
- adata adapter 改为 `list_market_current()` 无参优先；空表且签名确认支持时再使用 `code_list` fallback；缺 OHLC 时只通过 lite，不伪装为 full。
- `DEFAULT_SOURCE_POLICY` 更新为 `daily_kline: baostock -> akshare`、`full_realtime_quotes: easyquotation_sina -> easyquotation_tencent`、`lite_realtime_quotes: adata`、`index_realtime: easyquotation_sina -> easyquotation_tencent -> akshare`。
- 更新 README、SOURCE_CAPABILITY_MATRIX、LIVE_SOURCE_POLICY_DECISION、LIVE_SMOKE_TEST_REPORT、CODEX_FINAL_REPORT、PRODUCTION_CHECKLIST、PROJECT_STATE。

### Audit

- AKShare `stock_zh_a_hist` FAIL；`stock_zh_a_daily` raw 非空但首行严格映射 FAIL，adapter 修复后 `daily_kline` PASS。
- AKShare spot 全市场/分市场 FAIL；指数 EM FAIL；指数 Sina PASS。
- adata `get_market()` FAIL；`list_market_current()` 无参 FAIL；签名确认 `code_list` 返回 lite 字段 PASS、full FAIL。
- 最新 live gate：`post_close_gate=PASS`，`realtime_gate=PASS`，`index_realtime_gate=PASS`，`overall_live_gate=PASS`。
- 任务012.2F完成；允许进入任务013和 S0 盘后/实时沙盒，但本轮未执行任务013、未接入 S0，S0 正式生产仍禁止。

## 0.1.6 - 2026-06-12

### Added

- 新增 `scripts/debug_easyquotation_channels.py`，记录 easyquotation 新浪/腾讯 raw 返回与 router 质量闸门结果。
- 新增 `scripts/debug_optional_sources_live.py`，补测 efinance、Ashare、mootdx/pytdx。
- 新增 `EASYQUOTATION_CHANNEL_REPORT.md`、`OPTIONAL_BACKUP_SOURCE_REPORT.md`、`SOURCE_POLICY_V0_3_DECISION.md`。

### Changed

- `EasyQuotationAdapter` 支持按实例拆分为 `easyquotation_sina` 和 `easyquotation_tencent`。
- `MarketRouter` 自动注册 easyquotation 新浪与腾讯两个通道。
- `DEFAULT_SOURCE_POLICY` 更新为 `realtime_quotes/index_realtime: easyquotation_sina -> easyquotation_tencent`。
- `EFinanceAdapter` 股票实时改用 `get_latest_quote`，指数实时增加显式接口探测。
- live gate 的实时主/备规则改为新浪 primary、腾讯 backup；AKShare realtime 与 adata 不回默认链路。
- 更新 README、SOURCE_POLICY、SOURCE_CAPABILITY_MATRIX、LIVE_SOURCE_POLICY_DECISION、LIVE_SMOKE_TEST_REPORT、CODEX_FINAL_REPORT、PRODUCTION_CHECKLIST、PROJECT_STATE。

### Audit

- easyquotation_sina：`realtime_quotes` PASS，`index_realtime` PASS。
- easyquotation_tencent：`realtime_quotes` PASS，`index_realtime` PASS。
- efinance 0.5.8：专项 `realtime_quotes` PASS；`daily_kline` FAIL；`index_realtime` FAIL；完整 live smoke 中 realtime 亦出现远端断开，因此仅 optional。
- Ashare：当前索引无法安装，SKIP。
- mootdx 0.11.7：raw realtime/daily 有数据，但未通过标准 adapter gate；minute gate FAIL。
- pytdx 1.72：需要显式 TDX 服务器配置，SKIP。
- 最新 gate：`post_close_gate=FAIL`，`realtime_gate=PASS`，`index_realtime_gate=PASS`，`overall_live_gate=FAIL`。
- 任务012.2C完成但未达到整体门槛，禁止进入任务013，禁止任何 S0 接入。

## 0.1.5 - 2026-06-11

### Added

- 新增 `scripts/debug_akshare_latest_realtime.py`，专项测试 AKShare 最新实时原始接口。
- 新增 `scripts/debug_adata_latest_raw.py`，专项测试 adata 最新原始接口。
- 新增 `AKSHARE_LATEST_REALTIME_DEBUG_REPORT.md`、`ADATA_LATEST_RAW_DEBUG_REPORT.md`、`LATEST_SOURCE_ADAPTER_FIX_REPORT.md`、`SOURCE_POLICY_V0_2_DECISION.md`。

### Changed

- AKShare adapter 增加中英文字段映射，并显式使用 `stock_zh_index_spot_em(symbol=...)` 处理指数实时。
- adata adapter 改用 `list_market_current(code_list=...)`，并补充 `get_market()` 日 K 字段映射。
- `scripts/smoke_test_live.py` 拆分 `post_close_gate`、`realtime_gate`、`index_realtime_gate`、`overall_live_gate`。
- `DEFAULT_SOURCE_POLICY` 收紧为 `daily_kline: baostock`、`trade_calendar: baostock -> akshare`、实时与指数实时仅 easyquotation。
- 更新 README、SOURCE_POLICY、SOURCE_CAPABILITY_MATRIX、LIVE_SOURCE_POLICY_DECISION、LIVE_SMOKE_TEST_REPORT、CODEX_FINAL_REPORT、PRODUCTION_CHECKLIST、PROJECT_STATE。

### Audit

- AKShare 1.18.64、adata 2.9.5 已联网执行升级确认。
- AKShare `stock_zh_a_spot_em()` raw FAIL；`stock_zh_index_spot_em()` raw FAIL。
- adata `get_market()` raw FAIL；`list_market_current()` 返回 2 行但缺 `open/high/low`，标准映射 FAIL。
- 离线回归通过：pytest 28 passed、compileall PASS、offline smoke PASS、doctor_env PASS、ruff PASS。
- live smoke test 执行完成但 `overall_live_gate=FAIL`。任务012.2B完成但未通过，禁止进入任务013和任何 S0 接入。

## 0.1.4 - 2026-06-11

### Added

- 新增 `SOURCE_CAPABILITY_MATRIX.md`，记录任务012.1源-功能能力矩阵、缺字段、延迟、fallback、熔断和最终角色。
- 新增 `LIVE_SOURCE_POLICY_DECISION.md`，记录真实源生产角色、降级策略、默认链路和 live gate。
- 新增离线测试覆盖默认 source policy 和 live smoke 功能覆盖裁决。

### Changed

- `DEFAULT_SOURCE_POLICY` 调整为 Baostock 盘后优先、AKShare 盘后备源、easyquotation 实时优先；adata 和未验收 optional 源移出默认链路。
- `scripts/smoke_test_live.py` 从“单源整体 PASS”裁决改为按功能覆盖裁决。
- 更新 README、SOURCE_POLICY、LIVE_SMOKE_TEST_REPORT、CODEX_FINAL_REPORT、PRODUCTION_CHECKLIST、PROJECT_STATE。

### Audit

- 离线回归通过：pytest 28 passed、compileall PASS、offline smoke PASS、doctor_env PASS、ruff PASS。
- 最新 live 重跑：Baostock 和 easyquotation PASS；AKShare 与 adata FAIL；efinance、mootdx、Ashare SKIP。
- 最新 live gate 未通过：AKShare `daily_kline` FAIL 导致盘后日 K 仅 1 源 PASS；实时链路缺少备源。允许进入任务012.2做修复或补测，禁止进入任务013，禁止 S0 实时沙盒和 S0 正式生产。

## 0.1.3 - 2026-06-11

### Added

- 新增 `LIVE_SMOKE_TEST_REPORT.md`，记录任务012真实源 live smoke test 与源可用性审计结果。
- `scripts/smoke_test_live.py` 输出数据源摘要、接口摘要、依赖版本、响应耗时、缺失字段、fallback、熔断和审计日志写入状态。

### Changed

- live smoke test 从单源单接口探测扩展为源和接口矩阵审计。
- `CODEX_FINAL_REPORT.md`、`PROJECT_STATE.md`、`PRODUCTION_CHECKLIST.md` 更新任务012裁决。

### Audit

- 第一批依赖 AKShare、Baostock、easyquotation、adata 已安装并执行 live smoke test。
- Baostock、easyquotation PASS；AKShare、adata FAIL；efinance、mootdx、Ashare SKIP。
- 按任务012裁决规则，真实源 live smoke test 未通过，不允许进入任务013，不允许接入 S0 沙盒或 S0 正式生产。

## 0.1.2 - 2026-06-11

### Added

- 新增 `scripts/setup_dev_windows.bat`，在 Windows 下创建 `.venv` 并安装 `.[dev]`。
- 新增 `scripts/setup_dev_macos.sh`，在 macOS / Linux 下创建 `.venv` 并安装 `.[dev]`。
- 新增 `scripts/doctor_env.py`，输出 `logs/environment_report.json`。
- 新增 `ENVIRONMENT.md`，说明项目虚拟环境、doctor_env 和验收解释器标准。

### Changed

- Windows/macOS 测试脚本改为优先使用项目 `.venv`，不再依赖系统默认 `python`。
- 生产候选验收标准修正为 `.venv` 下通过 pytest、compileall、offline smoke test 和 doctor_env。
- ruff 未安装时记录 `SKIP`；ruff 已安装时运行并要求通过。
- 更新 README、PRODUCTION_CHECKLIST、PROJECT_STATE 和 CODEX_FINAL_REPORT 的环境可复现验收说明。

### Fixed

- 修复旧测试断言仍要求系统默认 `python` 的问题。
- 修复 ruff 报告的导入排序、上下文管理器和无抽象方法 ABC 标记问题。

## 0.1.1 - 2026-06-11

### Added

- 新增 `CURRENT_BASELINE.md`，记录基线审计、测试结果、风险点、生产化缺口和不可改动边界。
- 新增 `scripts/smoke_test_offline.py`，默认离线使用 FakeAdapter。
- 新增 `scripts/smoke_test_live.py`，仅在 `ENABLE_LIVE_SMOKE_TEST=1` 时访问真实源。
- 新增 `astock_source_router/core/data_usage_guard.py`，区分 `intraday`、`after_close`、`backtest` 的数据使用权限。
- 新增生产候选测试矩阵：日 K、实时行情、健康评分、熔断恢复、质量闸门、未来函数防火墙、UTF-8 输出。
- 新增 `PRODUCTION_CHECKLIST.md`。

### Changed

- 实时行情和历史日 K 标准字段补齐 `data_timestamp`。
- 质量闸门增强为可识别空表、缺字段、类型错误、目标日期异常、价格/成交额为 0、行数不足、实时数据过期、HTML / 验证码 / 风控页面。
- 审计日志扩展为 JSONL + 五张 SQLite 表。
- 健康评分增强为按 `function_name + source_name` 独立统计成功率、平均耗时、P95、空数据率、字段完整率、数据新鲜度和最近失败次数。
- Windows/macOS 测试脚本补齐 `pytest` 与 `compileall` 验收命令。
- README、免责声明、source policy、第三方说明和项目状态更新为生产候选边界。

### Security / Compliance

- 保持默认测试不联网。
- 保持第三方真实源为 optional dependencies。
- 明确不提供投资建议、交易信号、仓位建议、收益预测、自动交易或数据再分发服务。
