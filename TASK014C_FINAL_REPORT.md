# TASK014C_FINAL_REPORT

Generated at: 2026-06-12

## Final Verdict

```text
任务014C：完成
pytdx运行时自动切换：通过
最快服务器优先：通过
断线自动切换：通过
全部失败后 fallback easyquotation：通过
允许继续 5 日稳定性观察：是
独立项目是否可正常使用：是
S0正式生产：否
```

## Required Conclusions

| Item | Conclusion |
|---|---|
| 1. 任务014C是否完成 | 完成 |
| 2. pytdx adapter 是否读取 active server pool | 是，读取 `config/pytdx_servers_active.json` |
| 3. 是否按 latency 选择最快服务器 | 是，同一 role 内按 `latency_ms` 升序 |
| 4. primary 是否优先使用 | 是，`primary -> hot_backup -> backup` |
| 5. primary 失败是否自动切 hot_backup | 是，live failover PASS |
| 6. hot_backup 失败是否自动切 backup_pool | 是，live failover PASS |
| 7. backup_pool 全失败是否 fallback 到 easyquotation | 是，realtime/full/index 均 fallback 到 `easyquotation_sina` |
| 8. 是否记录 attempted_servers | 是，记录在 `pytdx_failover_attempts` / `attempted_servers` |
| 9. 是否记录 selected_server | 是 |
| 10. 是否记录 failover_reason | 是 |
| 11. 是否写入 JSONL 审计日志 | 是，`logs/source_router.jsonl` |
| 12. 是否写入 SQLite 审计日志 | 是，`logs/source_router.db` |
| 13. 是否新增 pytdx_runtime_failover_trace 表 | 是 |
| 14. 是否修改 source policy | 否 |
| 15. 是否破坏 easyquotation fallback | 否 |
| 16. 是否破坏 full/lite 边界 | 否，`lite_realtime_quotes` 仍为 adata-only |
| 17. 是否允许继续 5 日稳定性观察 | 是 |
| 18. 是否允许独立项目继续正常使用 | 是 |
| 19. 是否允许 S0 正式生产 | 否 |
| 20. 是否接入 S0/QMT/券商账户 | 否 |
| 21. 是否输出交易建议、候选股池、策略信号、买卖点、仓位、收益率、胜率或交易计划 | 否 |

## Implementation Summary

- Added runtime pytdx server records with role, latency, connect/quote status, disabled flag, and fake-fail test support.
- Added request-level pytdx failover for `realtime_quotes`, `full_realtime_quotes`, `index_realtime`, and `minute_kline`.
- Added `PytdxAllServersFailed` so router can distinguish all-pytdx-server failure and continue normal fallback.
- Added pytdx runtime metadata to DataFrame attrs, router result metadata, router fallback trace, JSONL payload, and SQLite audit.
- Added SQLite table `pytdx_runtime_failover_trace`.
- Added offline unit tests in `tests/test_pytdx_runtime_failover.py`.
- Added live debug script `scripts/debug_pytdx_runtime_failover.py`, gated by `ENABLE_PYTDX_FAILOVER_TEST=1`.

## Live Failover Result

Source: `logs/pytdx_runtime_failover_report.json`

| Scenario | Result |
|---|---|
| normal primary for realtime/full/index/minute | PASS |
| simulated primary fail -> hot_backup | PASS |
| simulated primary + hot_backup fail -> backup | PASS |
| simulated all pytdx fail -> easyquotation for realtime/full/index | PASS |
| all pytdx fail for minute_kline | SKIP by source policy; `minute_kline` is pytdx-only |

## Verification

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -X utf8 -m pytest -q` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m compileall -q astock_source_router tests examples` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\smoke_test_offline.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 scripts\doctor_env.py` | PASS |
| `.venv\Scripts\python.exe -X utf8 -m ruff check --no-cache .` | PASS |
| `ENABLE_PYTDX_FAILOVER_TEST=1 scripts\debug_pytdx_runtime_failover.py` | PASS |
| `ENABLE_LIVE_SMOKE_TEST=1 scripts\smoke_test_live.py` | PASS |

`ENABLE_SOURCE_SWITCH_CONSISTENCY_TEST=1 scripts\check_source_switch_consistency.py` was not rerun because this task did not change unit policy or standard field units/return schema.

## Output Files

- `scripts/debug_pytdx_runtime_failover.py`
- `tests/test_pytdx_runtime_failover.py`
- `PYTDX_RUNTIME_FAILOVER_REPORT.md`
- `PYTDX_RUNTIME_FAILOVER_DECISION.md`
- `TASK014C_FINAL_REPORT.md`
- `logs/pytdx_runtime_failover_report.json`
- `logs/source_router.jsonl`
- `logs/source_router.db`
- `config/pytdx_servers_active.json`

## Forbidden Scope Audit

- S0: not connected.
- QMT: not connected.
- Broker account: not connected.
- Cookie/token/account/login state: not added.
- Automatic trading: not added.
- Trading advice/candidate pool/strategy signals/buy-sell points/position/return/win-rate/trading plan: not output.
