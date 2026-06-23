# Source Policy

## 默认原则

1. 只做本地路由和适配，不做数据再分发。
2. 不内置 cookie、token、账号、券商登录态、QMT 或客户端登录态。
3. 不绕过源站限制，不做高频请求。
4. 数据源按 feature 字段级路由，不做全局单源依赖。
5. 盘后、full realtime、lite realtime 分层处理。
6. 每次请求必须记录审计日志。
7. 默认测试不联网；真实源 smoke test 必须设置 `ENABLE_LIVE_SMOKE_TEST=1`。
8. pytdx live 专项必须设置 `ENABLE_PYTDX_LIVE_TEST=1`。
9. 生产环境接入前必须先运行 smoke test，并检查字段、延迟、质量闸门和审计日志。
10. 新增真实源前必须先通过 adapter 单元测试、字段标准化测试和 schema drift 防火墙。

## 任务013.1源分级

### 默认链路

- pytdx：`realtime_quotes`、`full_realtime_quotes`、`index_realtime`、`minute_kline` 默认第一源。
- easyquotation：拆分为 `easyquotation_sina` 与 `easyquotation_tencent`，作为实时与指数实时 backup。
- AKShare：`daily_kline`、`trade_calendar` 盘后优先；指数实时仅 fallback；股票实时不作为默认主源。
- Baostock：`daily_kline`、`trade_calendar` 盘后 backup。
- adata：仅 `lite_realtime_quotes` 默认源；不得替代 full realtime。
- `stock_basic`：保持 Baostock -> AKShare。

### Optional / 禁用

- AKShare 股票实时接口：仅保留 optional，不作为实时主源。
- adata `full_realtime_quotes`：禁用；缺 `pre_close/open/high/low` 时不得补 full。
- efinance、Ashare、mootdx：仍为 optional，不进入默认链路。
- pytdx 当前仅 1 个 TDX 服务器 live PASS，必须保留 easyquotation fallback。

## 默认 source policy

代码中的可执行默认链路为：

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

策略说明中的 optional 源不写入可执行默认链路；只有完成 adapter 单元测试、字段标准化测试和显式 live smoke test 后，才允许进入默认链路。

`fake` 仅为默认离线测试 adapter，用于 adapter contract、schema drift 和
router smoke test。它的单位假设记录在 `config/source_unit_policy.json`，但
不属于真实数据源，不进入可执行默认链路，也不代表新增 source policy。

## live smoke test 验收

`scripts/smoke_test_live.py` 按五层 gate 裁决：

- `post_close_gate`：`daily_kline` 至少 AKShare + Baostock 双源 PASS，`trade_calendar` 至少 AKShare + Baostock 双源 PASS。
- `realtime_gate`：pytdx `realtime_quotes` / `full_realtime_quotes` PASS，且 easyquotation 至少 1 个 backup PASS。
- `index_realtime_gate`：pytdx 指数实时优先；若 pytdx 不支持指数实时，则 easyquotation / AKShare 指数组合 PASS 也可通过。
- `minute_gate`：pytdx `minute_kline` PASS 则 PASS；若当前版本声明 minute 非必选，可为 non-blocking WARN。
- `overall_live_gate`：盘后、实时和指数 gate 全部 PASS；minute 不阻断，除非后续版本声明 minute 为必选。

当前最新 live 重跑结论：`post_close_gate=PASS`，`realtime_gate=PASS`，`index_realtime_gate=PASS`，`minute_gate=PASS`，`overall_live_gate=PASS`。允许独立项目正常使用，允许 S0 只读沙盒但当前不接入，S0 正式生产仍禁止。

## full / lite realtime 边界

- `full_realtime_quotes` 必须包含 `pre_close/open/high/low`。
- `lite_realtime_quotes` 只要求 `last_price/volume/amount/pct_chg` 等轻量字段。
- lite 不得用于需要 OHLC 或前收的盘中逻辑。
- lite 不得伪装为 full。

## 质量失败与 fallback

以下情况必须视为质量失败并允许自动切源：

- 请求异常或超时。
- 空 DataFrame。
- 必需字段缺失。
- 字段类型错误。
- 目标日期异常。
- 价格或成交额异常为 0。
- 返回行数明显不足。
- 实时数据过期。
- 返回 HTML / 验证码 / 风控页面。

健康评分按 `function_name + source_name` 独立统计，不允许跨接口全局混用。默认执行顺序遵循 source policy；熔断打开时跳过对应源，质量失败时继续 fallback。

任务028新增 L6 Autonomous Control Layer。L6 不修改上述默认 source policy，
不新增真实源，不改变 full / lite 边界，不改变字段标准。它只在运行时对已经
允许且已注册的候选源做稳定性排序提示：`NORMAL` 源优先，`DEGRADED` /
`BLOCKED` 源后置；如果只剩单源，仍允许再次观察以恢复 `NORMAL`。
L6 不生成策略、预测、投资建议、候选股池、仓位建议、QMT / 券商动作或自动交易。

## schema drift 防火墙

任务023新增显式真实探测入口：

```text
python main.py --task source_schema_probe_live
```

该入口真实调用 AkShare `stock_zh_a_spot_em`、pytdx quote、pytdx kline、
`easyquotation_sina`、`easyquotation_tencent`，并写入：

```text
reports/latest/source_schema_probe_live.json
logs/source_schema_probe_live.jsonl
```

核心字段缺失、原始字段名变化或标准化后字段为空时，adapter 必须标记
`schema_drift` 或 `field_missing`，并在 `validate_result.diagnose` 中记录
漂移字段、缺失字段和拒绝原因。不得静默补 0，不得对外返回未通过
`validate_standard_output` 的 public records。

ETF 和北交所样本如当前源不支持，必须记录 `unsupported`，不得记为
provider failed。默认测试仍不得联网；该 live probe 只能通过显式命令运行。
