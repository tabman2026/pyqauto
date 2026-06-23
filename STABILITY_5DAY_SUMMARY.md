# STABILITY 5DAY SUMMARY

## 结论

- 生成时间：`2026-06-12T09:56:23.119401+00:00`
- 需要交易日：`5`
- 已完成交易日：`1`
- SKIP 日报数：`0`
- 已评估日报数：`1`
- 状态：`IN_PROGRESS`
- 结论：观察期未满 5 个交易日报告，不能形成 5 日通过结论。
- 是否允许作为 S0 只读沙盒稳定基础：`False`
- 是否允许 S0 正式生产：`False`

## 最近观察日

| 日期 | 交易日 | 计入 | daily | overall | pytdx状态 | primary | hot backup | easy fallback | AK/Bao daily | consistency | audit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260612 | True | True | PASS | PASS | 34 / server_pool_ready | {'ip': '58.63.254.191', 'port': 7709, 'source': 'pytdx_hq_hosts', 'grade': 'primary', 'latency_ms': 124.418, 'tested_at': '2026-06-12T09:44:18.073462+00:00'} | {'ip': '183.60.224.177', 'port': 7709, 'source': 'pytdx_hq_hosts', 'grade': 'hot_backup', 'latency_ms': 146.867, 'tested_at': '2026-06-12T09:43:39.450957+00:00'} | True | PASS/PASS | WARN | jsonl=True, db=True |

## 审计声明

- 本汇总只读取每日稳定性观察 JSON，不联网。
- 未接入 S0、QMT、券商账户或自动交易。
- 未输出候选股池、策略信号、交易计划、买卖点、仓位、收益率或胜率。
- 即使 5 日观察 PASS，S0 正式生产仍禁止。
