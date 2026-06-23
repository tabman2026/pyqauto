# AKSHARE_ADATA_CALLING_FIX_REPORT

生成时间：2026-06-12

## 1. 本轮修复范围

本轮依据最新官方文档和原始接口重测结果，修复 `astock_source_router/adapters/akshare_adapter.py` 与 `astock_source_router/adapters/adata_adapter.py` 中的调用方式、字段映射和实时质量分层问题。未接入 S0、QMT、券商账户或自动交易，未输出任何交易建议。

## 2. AKShare 结论

| 接口 | 最新文档调用 | raw 结果 | adapter gate | 处理 |
|---|---|---:|---:|---|
| `stock_zh_a_hist` | 6 位代码 | FAIL，远端断开 | 不恢复 | 不进默认链路 |
| `stock_zh_a_daily` | `sh/sz` 前缀 | 非空；首行缺前收导致严格 raw 映射 FAIL | PASS | 增加 `turnover` 映射、向前缓冲取数、推导 `pre_close/pct_chg` 后过滤回目标日期 |
| `stock_zh_a_spot_em` | 无参 | FAIL，远端断开 | FAIL | 不作为 full realtime 默认源 |
| `stock_sh/sz/bj_a_spot_em` | 无参 | FAIL，远端断开 | FAIL | 不作为 full realtime 默认源 |
| `stock_zh_index_spot_em` | 文档枚举 symbol | FAIL，远端断开 | 不作为依据 | 不恢复 EM 路径 |
| `stock_zh_index_spot_sina` | 无参 | PASS | PASS | 作为 AKShare index fallback 的可用依据 |

## 3. adata 结论

| 接口 | 最新文档调用 | raw 结果 | adapter gate | 处理 |
|---|---|---:|---:|---|
| `get_market(stock_code, k_type=1, start_date)` | 不传 `end_date` | FAIL，空表 | FAIL | `daily_kline` 继续禁用 |
| `list_market_current()` | 无参 | FAIL，空表 | 不作为 PASS | 保留无参失败结论 |
| `list_market_current(code_list=...)` | 签名确认 `(code_list=None)` 后调用 | PASS，返回轻量字段 | `lite_realtime_quotes` PASS / `full_realtime_quotes` FAIL | 仅加入 lite 默认链路 |

## 4. 已修 adapter

- AKShare：补 `full_realtime_quotes` 特征；`stock_zh_a_daily` 备用接口使用 `sh/sz` 前缀；映射 `turnover -> turnover_rate`；对备用日 K 向前取 30 天缓冲以推导 `pre_close/pct_chg`，再过滤回请求区间；指数实时在 EM 不可用时尝试 Sina。
- adata：`get_market()` 不再传 `end_date`，本地过滤日期；`list_market_current()` 无参优先，空表且签名支持时再用 `code_list` fallback；实时不伪造 `pre_close/open/high/low`；新增 `lite_realtime_quotes`。

## 5. 问题归因

- 旧 adapter 存在调用方式问题：adata 日 K 传入 `end_date`，实时优先使用 `code_list` 而不是先无参；AKShare daily 备用接口缺 `turnover` 映射和起始日前收缓冲。
- 旧实时质量闸门过严：缺 OHLC 的 adata 轻量实时被直接判为不可用。本轮拆分 full/lite 后，adata 可作为 lite，但不能替代 full。
- 本轮未删除质量闸门，未跳过字段检查，未把空表、缺字段、远端断开或异常值强行判 PASS。

## 6. 验收

| 项 | 结果 |
|---|---:|
| latest doc raw debug | 已生成 `logs/latest_doc_calling_report.json` |
| live smoke adapter gate | `overall_live_gate=PASS` |
| 修复文件 | `akshare_adapter.py`、`adata_adapter.py`、`schema.py`、`features.py`、`policy.py`、`smoke_test_live.py` |
| 是否接入 S0 | 否 |
| 是否包含交易建议 | 否 |
