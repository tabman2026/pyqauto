# STABILITY OBSERVATION RULES

生成日期：2026-06-12

## 观察周期

连续 5 个交易日。每天至少运行一次，建议盘后运行；如需观察实时链路，可在盘中额外运行一次。每个交易日以 `logs/stability_daily_YYYYMMDD.json` 作为可计入观察的审计凭证。

## 启用规则

- 默认测试不得联网。
- 每日观察必须显式设置 `ENABLE_STABILITY_WATCH=1`。
- 真实源 smoke test 和 source consistency 仍由每日观察脚本内部显式执行，并写入既有报告。
- Windows 下运行命令前执行 `chcp 65001`，Python 使用 `-X utf8`。
- JSON / JSONL 写入必须使用 UTF-8 和 `ensure_ascii=False`。

## 每日通过规则

每日必须同时满足：

1. `overall_live_gate=PASS`。
2. pytdx 至少 1 个服务器可用。
3. 如果 pytdx 只有 1 个服务器，必须保留 `single_server_warning`。
4. easyquotation_sina / easyquotation_tencent 至少 1 个通道可作为实时 fallback。
5. AKShare daily_kline 成功；若 AKShare 失败，Baostock daily_kline backup 必须成功。
6. AKShare 和 Baostock 的 trade_calendar 均可用。
7. source consistency 无 FAIL；WARN 只作为人工复核项。
8. adata 仅用于 `lite_realtime_quotes`，不得进入 `realtime_quotes` 或 `full_realtime_quotes`。
9. `source_router.jsonl` 和 `source_router.db` 有新增写入。
10. fallback trace、failure event、health score 写入结构完整。
11. 无 S0、QMT、券商账户、自动交易、候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率输出。

## 5 日通过规则

最近 5 个交易日报告必须全部通过每日规则。若 5 日内 pytdx 每天都只有 1 个可用服务器，可以继续使用独立项目，但必须保持 `single_server_warning`，不得声明高可用。

5 日通过只代表具备后续 S0 只读沙盒稳定性观察基础，不代表允许 S0 正式生产。

## 失败规则

出现任一情况即失败：

1. 任一日 `overall_live_gate=FAIL`。
2. pytdx 和 easyquotation 实时链路同时失败。
3. AKShare 和 Baostock 盘后链路同时失败。
4. source consistency 出现关键字段 FAIL。
5. adata lite 被误用于 full。
6. 审计日志缺失或 fallback trace 缺失。
7. 出现 S0、QMT、券商账户、自动交易、候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率输出。

## 禁止事项

本观察期禁止：

- 接入 S0。
- 接入 QMT。
- 接入券商账户。
- 自动交易。
- 输出候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划。
- 删除质量闸门、fallback、熔断或审计日志。
- 把 pytdx 单服务器状态宣传为高可用。
- 把 adata lite 当作 full。
- 删除免责声明。
