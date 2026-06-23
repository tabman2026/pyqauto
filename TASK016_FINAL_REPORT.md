# TASK016_FINAL_REPORT

生成时间：2026-06-12  
任务：任务016｜字段单位与切源一致性冻结

## 结论

任务016已完成。字段单位已冻结，source unit policy 已生成，单位一致性检查 `PASS`，切源一致性检查 `WARN` 且无 BLOCK。

| 项目 | 状态 |
|---|---|
| 字段单位冻结 | 完成 |
| source unit policy | 已生成 |
| volume 标准单位 | `share` |
| amount 标准单位 | `yuan` |
| pct_chg 标准口径 | `percent` |
| derived 字段 | `pytdx.pct_chg`，以及缺失源 `pct_chg` 时由价格推导的字段 |
| 存在单位 WARN 的源 | `pytdx.amount`、`easyquotation_sina.volume`、`easyquotation_tencent.volume`、`akshare.index_realtime.volume/amount`、`adata.lite_realtime_quotes.volume/amount`、`akshare_stock_zh_a_daily_low_frequency.volume` |
| 已校验切源路径 | `pytdx -> easyquotation_sina`、`easyquotation_sina -> easyquotation_tencent`、`akshare -> baostock`、`akshare_hist -> akshare_stock_zh_a_daily_low_frequency` |
| 切源 PASS | `akshare -> baostock` |
| 切源 WARN | `pytdx -> easyquotation_sina`、`easyquotation_sina -> easyquotation_tencent`、`akshare_hist -> akshare_stock_zh_a_daily_low_frequency` |
| 切源 FAIL | 无 |
| 是否发现 BLOCK | 否 |
| source policy 是否修改 | 否 |
| 是否新增数据源 | 否 |
| 是否接入 S0 | 否 |
| 是否接入 QMT | 否 |
| 是否接入券商账户 | 否 |
| 是否自动交易 | 否 |
| 是否输出交易建议 | 否 |
| 是否影响 5 日稳定性观察 | 否 |
| 是否允许继续 5 日稳定性观察 | 是 |
| 独立项目是否可继续正常使用 | 是 |
| 是否允许 S0 正式生产 | 否 |

## 已新增

```text
astock_source_router/core/unit_policy.py
astock_source_router/core/unit_normalizer.py
astock_source_router/core/source_switch_consistency.py
config/field_unit_policy.json
config/source_unit_policy.json
scripts/check_unit_consistency.py
scripts/check_source_switch_consistency.py
FIELD_UNIT_POLICY.md
SOURCE_UNIT_POLICY.md
SOURCE_SWITCH_CONSISTENCY_REPORT.md
FIELD_UNIT_FREEZE_REPORT.md
TASK016_FINAL_REPORT.md
```

## 切源路径

```text
pytdx -> easyquotation_sina
easyquotation_sina -> easyquotation_tencent
akshare -> baostock
akshare_hist -> akshare_stock_zh_a_daily_low_frequency
```

## 裁决

若离线回归、单位一致性检查、切源一致性检查均为 PASS 或 WARN 且无 BLOCK：

```text
任务016：完成
字段单位冻结：完成
切源一致性：WARN 无 BLOCK
是否允许继续 5 日稳定性观察：是
独立项目是否可继续正常使用：是
是否允许 S0 正式生产：否
```
