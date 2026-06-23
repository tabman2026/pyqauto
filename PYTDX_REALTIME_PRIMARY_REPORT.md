# PYTDX Realtime Primary Report

## 结论

- 生成时间：`2026-06-12T07:03:30.847370+00:00`
- live 启用：`True`
- pytdx 安装：`True`
- get_security_quotes：`PASS`
- realtime_quotes：`PASS`
- full_realtime_quotes：`PASS`
- index_realtime：`PASS`
- minute_kline：`PASS`
- pytdx 是否允许进入实时默认第一源：`True`

## 字段派生

- `pct_chg`: derived_from_pytdx_price_and_last_close
- `name`: derived_from_pytdx_get_security_list_or_builtin_index_alias
- `date`: derived_from_local_date_because_pytdx_quote_has_servertime_only
- `time`: derived_from_pytdx_servertime

## 字段警告

- `volume`: pytdx quote volume is kept as raw vol; cross-source consistency may flag unit differences
- `price`: no price scaling adjustment was applied; live values were checked for plausible A-share/index ranges

## 功能明细

| feature | status | row_count | missing_fields | warnings | server |
| --- | --- | ---: | --- | --- | --- |
| realtime_quotes | PASS | 2 |  |  | 180.153.18.170:7709 |
| full_realtime_quotes | PASS | 2 |  |  | 180.153.18.170:7709 |
| index_realtime | PASS | 4 |  |  | 180.153.18.170:7709 |
| minute_kline | PASS | 200 |  |  | 180.153.18.170:7709 |

## 测试标的

- 股票：`000001, 600519`
- 指数：`000001(上证指数), 399001(深证成指), 399006(创业板指), 000300(沪深300)`

## 审计结论

- 本脚本只验证 pytdx 行情读取与字段标准化，不接入 S0、QMT、券商账户或自动交易。
- 未内置 cookie、token、账号或券商登录态。
- 不输出交易建议、仓位建议、收益率承诺或交易计划。
- JSON 报告使用 UTF-8 和 `ensure_ascii=False` 写入。
