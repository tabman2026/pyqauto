# PYTDX_RUNTIME_FAILOVER_REPORT

- created_at: 2026-06-12T15:46:04.874502+00:00
- live_enabled: True
- overall_status: PASS
- active_config: config\pytdx_servers_active.json
- sqlite_pytdx_trace_rows_after: 43

## Cases

| scenario | feature | status | selected_source | selected_server_role | failover_count |
|---|---|---|---|---|---|
| normal_primary | realtime_quotes | PASS | pytdx | primary | 0 |
| primary_fake_fail | realtime_quotes | PASS | pytdx | hot_backup | 1 |
| primary_hot_fake_fail | realtime_quotes | PASS | pytdx | backup | 2 |
| normal_primary | full_realtime_quotes | PASS | pytdx | primary | 0 |
| primary_fake_fail | full_realtime_quotes | PASS | pytdx | hot_backup | 1 |
| primary_hot_fake_fail | full_realtime_quotes | PASS | pytdx | backup | 2 |
| normal_primary | index_realtime | PASS | pytdx | primary | 0 |
| primary_fake_fail | index_realtime | PASS | pytdx | hot_backup | 1 |
| primary_hot_fake_fail | index_realtime | PASS | pytdx | backup | 2 |
| normal_primary | minute_kline | PASS | pytdx | primary | 0 |
| primary_fake_fail | minute_kline | PASS | pytdx | hot_backup | 1 |
| primary_hot_fake_fail | minute_kline | PASS | pytdx | backup | 2 |
| all_pytdx_fake_fail | realtime_quotes | PASS | easyquotation_sina | None | 34 |
| all_pytdx_fake_fail | full_realtime_quotes | PASS | easyquotation_sina | None | 34 |
| all_pytdx_fake_fail | index_realtime | PASS | easyquotation_sina | None | 34 |
| all_pytdx_fake_fail | minute_kline | SKIP |  |  |  |

## Audit

- source_router_jsonl_exists: True
- source_router_db_exists: True
- pytdx_runtime_failover_trace_table: True

## Audit Conclusion

- pytdx adapter reads `config/pytdx_servers_active.json`: PASS.
- Runtime order is `primary -> hot_backup -> backup`, with same-role servers sorted by `latency_ms`: PASS.
- Runtime candidates require `connect_status=PASS` and `quote_status=PASS`; disabled servers are skipped: PASS.
- `realtime_quotes`, `full_realtime_quotes`, `index_realtime`, and `minute_kline` all selected the fastest primary in the normal path: PASS.
- Simulated primary failure switched to hot backup for all four pytdx interfaces: PASS.
- Simulated primary plus hot backup failure switched to the fastest backup server for all four pytdx interfaces: PASS.
- Simulated all pytdx servers failed caused router fallback to `easyquotation_sina` for realtime/full/index: PASS.
- `minute_kline` all-pytdx-failed fallback is SKIP by policy because `minute_kline` is pytdx-only and has no easyquotation minute fallback.
- JSONL audit exists at `logs/source_router.jsonl`: PASS.
- SQLite audit exists at `logs/source_router.db`: PASS.
- SQLite table `pytdx_runtime_failover_trace` exists and was written: PASS.
- Source policy was not changed: PASS.
- easyquotation fallback was preserved: PASS.
- full/lite realtime boundary was preserved: PASS.
- S0/QMT/broker account integration: NOT CONNECTED.
- Trading advice, candidate pool, strategy signals, buy/sell points, position, return, win-rate, and trading plan output: NOT OUTPUT.
