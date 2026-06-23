# PYTDX_RUNTIME_FAILOVER_DECISION

Generated at: 2026-06-12

## Decision

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

## Basis

- `PytdxAdapter` now loads `config/pytdx_servers_active.json` at runtime unless an explicit `PYTDX_SERVER_POOL` override is supplied.
- Active pool candidates are filtered to `connect_status=PASS` and `quote_status=PASS`; disabled servers are excluded.
- Runtime order is `primary -> hot_backup -> backup`, with same-role candidates sorted by `latency_ms`.
- Each pytdx request attempts the next server on `connect_timeout`, `connect_failed`, `quote_timeout`, `quote_empty`, `quote_schema_missing`, `quote_invalid_value`, `server_disabled`, or `unknown_error`.
- The selected pytdx server metadata is attached to returned result metadata and router fallback trace.
- If every pytdx server fails, `PytdxAllServersFailed` is raised and `MarketRouter` continues to the existing fallback chain.
- `realtime_quotes`, `full_realtime_quotes`, and `index_realtime` fallback to `easyquotation_sina -> easyquotation_tencent` after all pytdx servers fail.
- `minute_kline` remains pytdx-only by source policy; all-pytdx-failed fallback is intentionally not added.

## Audit

- JSONL audit: `logs/source_router.jsonl` exists.
- SQLite audit: `logs/source_router.db` exists.
- New SQLite table: `pytdx_runtime_failover_trace` exists and has runtime rows.
- Live failover report: `logs/pytdx_runtime_failover_report.json` status `PASS`.
- Source policy unchanged.
- easyquotation fallback preserved.
- `lite_realtime_quotes` remains adata-only and was not promoted to full realtime.

## Restrictions

- S0 not connected.
- QMT not connected.
- Broker account not connected.
- No cookie, token, account, or broker login state was added.
- No automatic trading logic was added.
- No trading advice, candidate pool, strategy signal, buy/sell point, position, return, win-rate, or trading plan was output.
