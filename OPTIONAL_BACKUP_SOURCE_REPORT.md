# OPTIONAL_BACKUP_SOURCE_REPORT

生成时间：2026-06-11T18:43:24.127962+00:00

## 1. 源能力结论

| source | daily_kline | realtime_quotes | index_realtime | minute_kline |
|---|---:|---:|---:|---:|
| efinance | FAIL | PASS | FAIL | SKIP |
| ashare | SKIP | SKIP | SKIP | SKIP |
| mootdx | SKIP | SKIP | SKIP | FAIL |
| pytdx | SKIP | SKIP | SKIP | SKIP |

备注：efinance `realtime_quotes` 在本专项脚本中通过质量闸门，但随后完整 `smoke_test_live.py` 同轮运行出现 `RemoteDisconnected`，因此仅保留为 optional 候选，不进入默认链路。mootdx raw `quotes` / `bars` 虽返回数据，但未通过本项目标准 adapter 质量闸门，不计入默认源。

## 2. 明细

| source | feature | api | status | gate | rows | columns | duration_ms | missing_fields | warnings | reason |
|---|---|---|---:|---:|---:|---|---:|---|---|---|
| efinance | daily_kline | efinance.stock.get_quote_history | FAIL | FAIL | 0 |  | 2519.801 |  |  | router_quality_gate_fail |
| efinance | daily_kline | efinance.stock.get_quote_history | FAIL | FAIL | 0 |  | 1427.859 |  |  | router_quality_gate_fail |
| efinance | realtime_quotes | efinance.stock.get_latest_quote | PASS | PASS | 2 | date, time, code, name, last_price, pre_close, open, high, low, volume, amount, pct_chg, source, source_latency_ms, source_status, data_timestamp | 673.391 |  |  | router_quality_gate_pass |
| efinance | index_realtime | efinance.stock.get_realtime_quotes('沪深系列指数') | FAIL | FAIL | 0 |  | 1053.438 |  |  | router_quality_gate_fail |
| ashare | daily_kline | Ashare import | SKIP | SKIP | 0 |  | None |  |  | dependency_not_installed_or_unavailable: Ashare/ashare |
| ashare | daily_kline | Ashare import | SKIP | SKIP | 0 |  | None |  |  | dependency_not_installed_or_unavailable: Ashare/ashare |
| ashare | realtime_quotes | Ashare import | SKIP | SKIP | 0 |  | None |  |  | dependency_not_installed_or_unavailable: Ashare/ashare |
| ashare | minute_kline | Ashare import | SKIP | SKIP | 0 |  | None |  |  | dependency_not_installed_or_unavailable: Ashare/ashare |
| ashare | index_realtime | Ashare import | SKIP | SKIP | 0 |  | None |  |  | dependency_not_installed_or_unavailable: Ashare/ashare |
| mootdx | minute_kline | MootdxAdapter.fetch_minute_kline | FAIL | FAIL | 0 |  | 388.235 | datetime, code, open, high, low, close, volume, amount | empty_dataframe, missing_required_columns | router_quality_gate_fail |
| mootdx | realtime_quotes | mootdx.Quotes.quotes | PASS | SKIP | 2 | market, code, active1, price, last_close, open, high, low, servertime, reversed_bytes0, reversed_bytes1, vol, cur_vol, amount, s_vol, b_vol, reversed_bytes2, reversed_bytes3, bid1, ask1, bid_vol1, ask_vol1, bid2, ask2, bid_vol2, ask_vol2, bid3, ask3, bid_vol3, ask_vol3, bid4, ask4, bid_vol4, ask_vol4, bid5, ask5, bid_vol5, ask_vol5, reversed_bytes4, reversed_bytes5, reversed_bytes6, reversed_bytes7, reversed_bytes8, reversed_bytes9, active2, volume | 284.624 |  |  | raw_non_empty_no_adapter_gate |
| mootdx | daily_kline | mootdx.Quotes.bars | PASS | SKIP | 5 | open, close, high, low, vol, amount, year, month, day, hour, minute, datetime, volume | 356.624 |  |  | raw_non_empty_no_adapter_gate |
| pytdx | realtime_quotes | pytdx.hq.TdxHq_API.get_security_quotes | SKIP | SKIP | 0 |  | None |  |  | requires_explicit_tdx_server_host_and_market_selection |
| pytdx | minute_kline | pytdx.hq.TdxHq_API.get_security_bars | SKIP | SKIP | 0 |  | None |  |  | requires_explicit_tdx_server_host_and_market_selection |
| pytdx | daily_kline | pytdx.hq.TdxHq_API.get_security_bars | SKIP | SKIP | 0 |  | None |  |  | requires_explicit_tdx_server_host_and_market_selection |

## 3. 使用边界

- efinance 即使通过，也仅按 optional/default backup with notice 处理，不宣传为商用级源。
- Ashare 当前依赖不可用或 API 未确认时仅 SKIP，不进入默认链路。
- mootdx/pytdx 需要通达信服务器连接或额外网络配置时不作为 V0.3 live gate 强阻断项。
- 本报告未接入 S0，未输出任何交易建议。
