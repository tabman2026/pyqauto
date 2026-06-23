# SOURCE_CAPABILITY_MATRIX

生成时间：2026-06-12

依据：`logs/latest_doc_calling_report.json`、`logs/smoke_test_report.json`。

## 1. 当前 live 能力矩阵

| source_name | full_realtime_quotes | lite_realtime_quotes | daily_kline | trade_calendar | index_realtime | final_role |
|---|---:|---:|---:|---:|---:|---|
| akshare | FAIL | SKIP | PASS | PASS | PASS | `daily_kline` backup；`trade_calendar` backup；`index_realtime` third fallback |
| baostock | SKIP | SKIP | PASS | PASS | SKIP | `daily_kline` primary；`trade_calendar` primary |
| easyquotation_sina | PASS | SKIP | SKIP | SKIP | PASS | full realtime/index primary |
| easyquotation_tencent | PASS | SKIP | SKIP | SKIP | PASS | full realtime/index backup |
| adata | FAIL | PASS | FAIL | FAIL | SKIP | `lite_realtime_quotes` only |
| efinance | SKIP | SKIP | FAIL | SKIP | FAIL | optional only |
| mootdx | SKIP | SKIP | SKIP | SKIP | SKIP | optional only；minute FAIL |
| ashare | SKIP | SKIP | SKIP | SKIP | SKIP | dependency/adapter unavailable |

## 2. AKShare / adata 最新文档专项

| provider | API | raw 结论 | 标准映射结论 |
|---|---|---:|---|
| AKShare | `stock_zh_a_hist` | FAIL | 不恢复 |
| AKShare | `stock_zh_a_daily` | 非空，但首行严格映射 FAIL | adapter 缓冲修复后 `daily_kline` PASS |
| AKShare | `stock_zh_a_spot_em` / 分市场 spot | FAIL | `full_realtime_quotes` 禁用 |
| AKShare | `stock_zh_index_spot_em` | FAIL | EM 禁用 |
| AKShare | `stock_zh_index_spot_sina()` | PASS | `index_realtime` fallback PASS |
| adata | `get_market()` | FAIL，空表 | `daily_kline` 禁用 |
| adata | `list_market_current()` 无参 | FAIL，空表 | 不作为 PASS |
| adata | `list_market_current(code_list=...)` | PASS | `lite_realtime_quotes` PASS；full FAIL |

## 3. Gate 结果

| gate | 结果 | 说明 |
|---|---:|---|
| `post_close_gate` | PASS | `daily_kline`：Baostock、AKShare PASS；`trade_calendar`：Baostock、AKShare PASS |
| `realtime_gate` | PASS | full realtime：`easyquotation_sina` primary PASS；`easyquotation_tencent` backup PASS |
| `index_realtime_gate` | PASS | `easyquotation_sina` primary PASS；`easyquotation_tencent` backup PASS；AKShare fallback PASS |
| `overall_live_gate` | PASS | 三个分层 gate 均通过 |

## 4. 审计结论

- 恢复默认链路：AKShare `daily_kline`、AKShare `index_realtime`、adata `lite_realtime_quotes`。
- 继续禁用：AKShare `full_realtime_quotes`、AKShare hist、AKShare index EM、adata `daily_kline/full_realtime_quotes`。
- lite 不得替代 full。
- 允许进入任务013，但本轮未执行任务013。
- 允许 S0 盘后只读沙盒与 S0 实时沙盒；S0 正式生产仍禁止。
