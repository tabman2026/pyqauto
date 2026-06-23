# LATEST_SOURCE_ADAPTER_FIX_REPORT

生成时间：2026-06-11

任务：任务012.2B｜AKShare 与 adata 最新接口专项重测

## 1. 修复范围

本轮未推倒重写项目，未大改 `MarketRouter`，未删除 fallback、熔断、审计日志或质量闸门，未接入 S0、QMT、券商账户、cookie、token 或自动交易能力。

修改文件：

- `astock_source_router/adapters/akshare_adapter.py`
- `astock_source_router/adapters/adata_adapter.py`
- `scripts/smoke_test_live.py`
- `astock_source_router/core/policy.py`
- `tests/test_live_smoke_acceptance.py`
- `scripts/debug_akshare_latest_realtime.py`
- `scripts/debug_adata_latest_raw.py`

## 2. AKShare adapter

| 项目 | 结果 |
|---|---|
| `realtime_quotes` | 仍使用 `ak.stock_zh_a_spot_em()`；新增中文和常见英文字段映射兼容 |
| `index_realtime` | 改为显式调用 `ak.stock_zh_index_spot_em(symbol=...)`，优先 `沪深重要指数`，必要时低频 fallback 到 `上证系列指数`、`深证系列指数` |
| 代码格式 | 继续由 router 标准化为 6 位字符串 |
| 日期格式 | adapter 输出 `YYYY-MM-DD` |
| 缺字段处理 | 不伪造缺失字段；缺字段由 router 质量闸门判 FAIL |

本轮最终 raw/live 结果中 AKShare `stock_zh_a_spot_em()`、`stock_zh_index_spot_em()` 均出现远端断开；因此未恢复 AKShare 实时或指数实时默认链路。AKShare `stock_zh_a_hist` live 仍 FAIL，已从 `daily_kline` 默认链路移除。

## 3. adata adapter

| 项目 | 结果 |
|---|---|
| `daily_kline` | 继续使用 `adata.stock.market.get_market()`；补充 `turnover_ratio -> turnover_rate`、`change_pct -> pct_chg` 等字段映射 |
| `realtime_quotes` | 改为最新参数 `adata.stock.market.list_market_current(code_list=...)` |
| `pre_close` | 当接口返回 `price/close + change_pct` 时可推导 |
| `open/high/low` | `list_market_current()` 官方包装未提供，不伪造，不强行判 PASS |
| 指数实时 | 未发现 adata 明确实时指数接口，继续 SKIP |

adata `list_market_current(code_list=["000001", "600519"])` 能返回 2 行，但缺 `open/high/low`，标准 `realtime_quotes` 映射失败；`get_market()` 本轮返回空表。因此未恢复 adata 默认链路。

## 4. live gate 修正

`scripts/smoke_test_live.py` 已拆分四层 gate：

| gate | 通过条件 | 本轮结果 |
|---|---|---:|
| `post_close_gate` | `daily_kline` 至少 2 源 PASS，`trade_calendar` 至少 2 源 PASS | FAIL |
| `realtime_gate` | `easyquotation` PASS，且 AKShare 或 adata 至少一个备用源 PASS | FAIL |
| `index_realtime_gate` | `easyquotation` PASS，且 AKShare 或 adata 至少一个备用源 PASS | FAIL |
| `overall_live_gate` | 以上三项全部 PASS | FAIL |

## 5. source policy 裁决

代码中当前默认链路：

```text
daily_kline:     baostock
trade_calendar:  baostock -> akshare
realtime_quotes: easyquotation
index_realtime:  easyquotation
minute_kline:    <no default source>
stock_basic:     baostock -> akshare
```

未恢复链路：

- AKShare `realtime_quotes`
- AKShare `index_realtime`
- AKShare `daily_kline`
- adata `daily_kline`
- adata `realtime_quotes`
- adata `index_realtime`

## 6. 验收结论

- 未强行判 PASS。
- 未删除字段检查、零值检查、fallback、熔断或审计日志。
- adapter 已按最新签名做兼容修复，但 live smoke test 未通过。
- 任务012.2B：完成但未通过。
- 进入任务013：否。
- S0 盘后只读沙盒：否。
- S0 实时沙盒：否。
- S0 正式生产：否。
