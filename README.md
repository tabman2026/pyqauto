# pyqauto 1.0.0rc1 Release Candidate

Current stable recommendation: `pyqauto==0.3.1`.

`pyqauto==1.0.0rc1` is a prerelease test candidate for V1 API freeze
validation. It is not the final `1.0.0` release and is not the default
recommendation for all users.

Install the RC explicitly:

```bash
python -X utf8 -m pip install pyqauto==1.0.0rc1 -i https://pypi.org/simple
```

Or allow prereleases:

```bash
python -X utf8 -m pip install --pre pyqauto -i https://pypi.org/simple
```

Rollback to the current stable release:

```bash
python -X utf8 -m pip install --force-reinstall pyqauto==0.3.1 -i https://pypi.org/simple
```

# A股多源行情源路由器

Python 包名：`astock_source_router`

本项目是一个面向 A 股的本地多源行情路由器 / 适配器框架。它在用户本地调用第三方开源库公开 API，把 pytdx、AKShare、Baostock、easyquotation、adata、efinance、mootdx 等可选数据源封装为统一入口，并提供字段标准化、fallback、健康评分、熔断、缓存、限频和审计日志。

本项目不是金融数据服务端，不做行情数据对外再分发，不提供投资建议，不提供买卖点、荐股、候选股池、仓位建议、策略信号、收益率预测或自动交易能力。

## 当前状态

任务014B已完成 pytdx 服务器池扩容与本地自动稳定性观察；V0.6 source policy 继续冻结：

- pytdx 已通过实时主源专项 live 验证，进入实时默认第一源。
- pytdx server pool 已扩容：候选 103 个，PASS 34 个，状态 `server_pool_ready`。
- 当前 primary server：`58.63.254.191:7709`；hot backup：`183.60.224.177:7709`。
- AKShare 已调整为盘后优先源；Baostock 为盘后 backup。
- easyquotation_sina / easyquotation_tencent 继续作为实时 backup。
- adata 仍仅作为 `lite_realtime_quotes`。
- 最新一致性校验：整体 `WARN`、无 `FAIL`。
- 最新 live smoke gate：`overall_live_gate=PASS`。
- 新增连续 5 个交易日稳定性观察脚本、交易日过滤和 Windows 定时任务。
- 最新稳定性观察：`daily_acceptance=PASS`，5 日汇总 `IN_PROGRESS`（当前 1/5 个交易日）。
- 任务023新增真实源 schema probe：`python main.py --task source_schema_probe_live`。
- live probe 输出 `reports/latest/source_schema_probe_live.json` 和
  `logs/source_schema_probe_live.jsonl`，用于识别字段漂移和拒绝未验证数据。
- 允许独立项目正常使用。
- 允许进入连续 5 个交易日稳定性观察；当前不接入 S0。
- S0 正式生产仍禁止。

## 能力边界

可以做：

- 本地调用第三方库公开 API。
- 多源 adapter、字段标准化、质量闸门、fallback、熔断、健康评分。
- 本地缓存、限频、JSONL + SQLite 审计日志。
- 默认离线测试和显式启用的真实源 smoke / consistency test。
- 显式运行真实源 schema probe，检查 AkShare、pytdx、easyquotation
  当前返回字段、单位规则和标准化映射。

不做：

- 不复制第三方项目核心代码。
- 不内置 cookie、token、账号、券商登录态、QMT 或客户端登录态。
- 不绕过源站限制，不做高频抓取。
- 不提供行情 API 服务端或数据再分发服务。
- 不输出任何投资建议、交易计划或自动交易逻辑。

## 安装

默认安装只依赖 `pandas`：

```bash
python -X utf8 -m pip install astock-source-router
```

按需安装可选数据源：

```bash
python -X utf8 -m pip install "astock-source-router[akshare]"
python -X utf8 -m pip install "astock-source-router[baostock]"
python -X utf8 -m pip install "astock-source-router[realtime]"
python -X utf8 -m pip install "astock-source-router[eastmoney]"
python -X utf8 -m pip install "astock-source-router[tdx]"
python -X utf8 -m pip install "astock-source-router[all]"
```

Windows 本地开发：

```bat
scripts\setup_dev_windows.bat
scripts\run_tests_windows.bat
```

macOS / Linux：

```bash
bash scripts/setup_dev_macos.sh
bash scripts/run_tests_macos.sh
```

## 快速开始

```python
from astock_source_router import MarketRouter

router = MarketRouter(auto_register=True)

df = router.get_realtime_quotes(["000001", "600519"])
print(df)

daily = router.get_daily_kline("600519", start_date="20250101", end_date="20250611")
print(daily)

print(router.health_report())
print(router.autonomy_status())
print(router.recovery_state())
print(router.anomaly_report())
print(router.source_weight_decay())
```

## 默认字段级路由

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

说明：pytdx 作为实时主源走通达信行情服务器链路；当前 active pool 有 34 个 live PASS 服务器，`server_pool_ready=True`，仍必须保留 easyquotation fallback。`easyquotation_sina` 与 `easyquotation_tencent` 是同一 `easyquotation` 库下的不同底层通道，不等价于完全独立库级双源。AKShare 优先用于盘后，不作为股票实时主源。adata 仅作为 `lite_realtime_quotes`，不得替代 full realtime。`efinance`、`Ashare`、`mootdx` 仍为 optional。

## 标准字段

### 完整实时行情 `full_realtime_quotes`

```text
code, name, last_price, pre_close, open, high, low, volume, amount,
pct_chg, source, source_latency_ms, source_status, data_timestamp
```

`realtime_quotes` 保持兼容，并按 full 规则验收。

### 轻量实时行情 `lite_realtime_quotes`

```text
code, name, last_price, volume, amount, pct_chg,
source, source_latency_ms, source_status, data_timestamp
```

lite 不得用于需要 `pre_close/open/high/low` 的盘中逻辑，不得伪装为 full，不得直接喂给 S0 full realtime 字段。

### 历史日 K `daily_kline`

```text
date, code, open, high, low, close, pre_close, volume, amount,
turnover_rate, pct_chg, adjust_type, source, source_latency_ms,
source_status, data_timestamp
```

## 质量闸门

路由器会把以下情况判定为质量失败并尝试 fallback：

- 空 DataFrame。
- 必需字段缺失。
- 字段类型错误。
- 目标日期异常。
- 价格字段异常为 0。
- 成交额异常为 0。
- 返回行数明显不足。
- 实时数据过期。
- 返回 HTML / 验证码 / 风控页面。

## L6 自治控制层

任务028新增 Autonomous Control Layer。该层只用于行情源运行稳定性：
自动恢复、异常识别、分数衰减和 schema drift 自愈。它不会改写默认
source policy，不新增真实数据源，不输出投资建议、策略信号、选股结果、
收益预测、仓位建议或自动交易逻辑。

公开 API：

```python
router.autonomy_status()
router.recovery_state()
router.anomaly_report()
router.source_weight_decay()
```

衰减模型固定为：

```text
score = old * 0.9 + new * 0.1
```

L6 会把失败源标记为 `DEGRADED`，成功恢复后回到 `NORMAL`；schema drift
降低并通过后解除 `BLOCKED`。异常检测仅用于识别 sudden full failure、
temporary instability 和 observation window，不用于交易或预测。

详见 `docs/AUTONOMOUS_CONTROL_LAYER.md`。

## 一致性校验

默认不联网：

```bat
.venv\Scripts\python.exe -X utf8 scripts\check_source_consistency.py
```

真实源一致性校验必须显式启用：

```powershell
$env:ENABLE_SOURCE_CONSISTENCY_TEST="1"
.venv\Scripts\python.exe -X utf8 scripts\check_source_consistency.py
```

输出：

```text
logs/source_consistency_report.json
SOURCE_CONSISTENCY_REPORT.md
```

当前任务013.1结果：

- `daily_kline`：WARN，成交量单位差异和 `pct_chg` 差异；AKShare 当前使用 `stock_zh_a_hist`。
- `trade_calendar`：PASS。
- `full_realtime_quotes`：WARN，pytdx 主源与 easyquotation 备源字段齐全，存在跨源单位/涨跌幅/timestamp lag 报警。
- `index_realtime`：WARN，pytdx 优先，easyquotation/AKShare fallback 保留，存在单位或 timestamp lag 报警。
- full/lite 边界：PASS。

## Smoke Test

默认离线 smoke test 不联网：

```bat
.venv\Scripts\python.exe -X utf8 scripts\smoke_test_offline.py
```

真实源 smoke test 必须显式启用：

```powershell
$env:ENABLE_LIVE_SMOKE_TEST="1"
.venv\Scripts\python.exe -X utf8 scripts\smoke_test_live.py
```

结果写入：

```text
logs/smoke_test_report.json
```

当前 live gate：

```text
post_close_gate=PASS
realtime_gate=PASS
index_realtime_gate=PASS
minute_gate=PASS
overall_live_gate=PASS
```

pytdx 专项 live 验证：

```powershell
$env:ENABLE_PYTDX_LIVE_TEST="1"
.venv\Scripts\python.exe -X utf8 scripts\debug_pytdx_server_pool.py
.venv\Scripts\python.exe -X utf8 scripts\debug_pytdx_realtime.py
```

结果写入：

```text
logs/pytdx_server_pool_report.json
logs/pytdx_realtime_primary_report.json
PYTDX_SERVER_POOL_REPORT.md
PYTDX_REALTIME_PRIMARY_REPORT.md
```

pytdx server pool refresh 必须显式启用：

```powershell
chcp 65001 | Out-Null
$env:ENABLE_PYTDX_SERVER_REFRESH="1"
.venv\Scripts\python.exe -X utf8 scripts\pytdx_server_pool_refresh.py
```

输出：

```text
logs/pytdx_server_pool_refresh.json
config/pytdx_servers_active.json
PYTDX_SERVER_POOL_EXPANSION_REPORT.md
```

当前 active pool：

```text
server_pool_status=server_pool_ready
available_server_count=34
primary=58.63.254.191:7709
hot_backup=183.60.224.177:7709
single_server_warning=False
```

## 稳定性观察

任务014B扩展连续 5 个交易日稳定性观察机制，不改变 V0.6 source policy，不接入 S0、QMT、券商账户或自动交易。观察脚本支持交易日过滤：非交易日输出 SKIP，不计入 5 日观察。

每日观察必须显式启用：

```powershell
chcp 65001 | Out-Null
$env:ENABLE_STABILITY_WATCH="1"
.venv\Scripts\python.exe -X utf8 scripts\daily_stability_watch.py
```

每日输出：

```text
logs/stability_daily_YYYYMMDD.json
reports/STABILITY_DAILY_YYYYMMDD.md
```

5 日汇总：

```powershell
chcp 65001 | Out-Null
.venv\Scripts\python.exe -X utf8 scripts\stability_summary.py
```

汇总输出：

```text
STABILITY_5DAY_SUMMARY.md
logs/stability_5day_summary.json
```

Windows 自动观察：

```bat
scripts\run_stability_watch_windows.bat
scripts\install_stability_watch_task_windows.bat
scripts\uninstall_stability_watch_task_windows.bat
```

当前计划任务已安装：

```text
任务名：A股行情源路由器_稳定性观察
默认时间：15:40
执行目标：scripts\run_stability_watch_windows.bat --scheduled
```

不足 5 个交易日报告时，汇总状态为 `IN_PROGRESS`。连续 5 个交易日全部满足规则后，才可作为后续 S0 只读沙盒稳定性基础；S0 正式生产仍禁止。

当前首日输出：

```text
logs/stability_daily_20260612.json
reports/STABILITY_DAILY_20260612.md
STABILITY_5DAY_SUMMARY.md
PYTDX_SERVER_POOL_EXPANSION_REPORT.md
AUTO_STABILITY_WATCH_REPORT.md
TASK014B_FINAL_REPORT.md
```

## 审计日志

默认输出：

```text
logs/source_router.jsonl
logs/source_router.db
```

JSON / JSONL 使用 UTF-8 写入，中文输出使用 `ensure_ascii=False`。

任务023新增 live schema probe 输出：

```text
reports/latest/source_schema_probe_live.json
logs/source_schema_probe_live.jsonl
```

live schema probe 会记录 `source_name`、`source_api`、原始字段、dtype、
样本行、`raw_to_standard_mapping`、`unit_rules`、`validate_result` 和
`adapter_status`。核心字段缺失或字段名漂移时标记 `schema_drift` /
`field_missing`，不静默补 0，不返回未通过 `validate_standard_output` 的
public records。`diagnose` 会显示最新 live probe 的漂移字段和拒绝原因。

# TASK023 UPDATE - 2026-06-21

任务023已完成真实数据源 schema 探测与漂移防火墙：新增
`python main.py --task source_schema_probe_live`，真实入口覆盖
AkShare `stock_zh_a_spot_em`、pytdx quote、pytdx kline、
`easyquotation_sina`、`easyquotation_tencent`。本任务不新增交易功能，
不生成候选股池、买卖信号、收益率、胜率、QMT 或自动交易逻辑。

验收结果：`python -X utf8 -m pytest` 通过，`python -X utf8 -m ruff check .`
通过。

## 生产使用提示

第三方免费公开源可能随时变更字段、限流、权限和可用性。生产环境接入前必须先运行 smoke test 和 source consistency test，并以第三方项目及源站规则为准。S0 正式生产仍禁止；当前只允许独立项目正常使用和 S0 只读沙盒边界验证，且本轮不接入 S0。
# TASK016 UPDATE - 2026-06-12

字段单位与切源一致性已冻结：`volume` 标准单位为 `share`，`amount` 标准单位为 `yuan`，`pct_chg` 标准口径为 `percent`。源单位假设记录在 `config/source_unit_policy.json`，字段标准记录在 `config/field_unit_policy.json`。单位检查脚本为 `scripts/check_unit_consistency.py`，切源检查脚本为 `scripts/check_source_switch_consistency.py`。任务016未修改 source policy，未新增数据源，未接入 S0/QMT/券商账户，未自动交易，未输出任何交易建议。

Task030 为 offline `fake` 测试 adapter 补充了显式单位假设，用于 adapter
contract 和 router smoke test。`fake` 不是真实数据源，不进入默认 source
policy，不改变任何真实源字段标准。
# TASK014C UPDATE - 2026-06-12

任务014C已完成并通过：pytdx adapter 运行时读取 `config/pytdx_servers_active.json`，按 `primary -> hot_backup -> backup` 使用服务器，同级按 `latency_ms` 升序。运行时只使用 `connect_status=PASS` 且 `quote_status=PASS` 的服务器，并跳过 disabled 服务器。

已验证 `realtime_quotes`、`full_realtime_quotes`、`index_realtime`、`minute_kline`：正常路径使用 primary `58.63.254.191:7709`；primary 失败自动切 hot backup `183.60.224.177:7709`；primary + hot backup 失败自动切 backup `119.29.19.242:7709`；pytdx 全部失败后，`realtime_quotes`、`full_realtime_quotes`、`index_realtime` fallback 到 `easyquotation_sina -> easyquotation_tencent`。`minute_kline` 保持 pytdx-only，不新增 easyquotation minute fallback。

运行时审计写入 `logs/source_router.jsonl`、`logs/source_router.db` 和 `logs/pytdx_runtime_failover_report.json`。SQLite 已新增 `pytdx_runtime_failover_trace` 表；返回 metadata / fallback trace 包含 `pytdx_server_ip`、`pytdx_server_port`、`pytdx_server_role`、`pytdx_server_latency_ms`、`pytdx_failover_attempts`、`selected_server` 和 `failover_reason`。

source policy 未修改，easyquotation fallback 未破坏，full/lite 边界未破坏。允许继续 5 日稳定性观察，允许独立项目继续正常使用，S0 正式生产仍禁止。未接入 S0/QMT/券商账户，未输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。
