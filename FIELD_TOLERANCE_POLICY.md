# FIELD_TOLERANCE_POLICY

生成时间：2026-06-12

本文件冻结任务013使用的字段一致性报警阈值。阈值只用于多源字段一致性报警、审计和人工复核，不产生任何交易判断、策略信号、买卖点、仓位建议或收益率预测。

## 适用范围

- `daily_kline`：baostock 与 akshare 的历史日 K 字段比较。
- `trade_calendar`：baostock 与 akshare 的交易日集合比较。
- `full_realtime_quotes`：easyquotation 新浪通道与腾讯通道的完整实时字段比较。
- `index_realtime`：easyquotation 新浪通道、腾讯通道与 AKShare 指数新浪接口的指数实时字段比较。
- `lite_realtime_quotes`：只做字段边界检查，不参与 full 字段精度裁决。

## 阈值

| 字段类型 | 阈值 | 处理方式 |
|---|---:|---|
| 价格字段绝对差 | `<= 0.01` | 超阈值记录 WARN |
| 价格字段相对差 | `<= 0.05%` | 与绝对差同时超阈值时记录 WARN |
| 成交量相对差 | `<= 5%` | 允许先记录单位比例，不改写原始数据 |
| 成交额相对差 | `<= 5%` | 允许先记录单位比例，不改写原始数据 |
| 涨跌幅绝对差 | `<= 0.05` 个百分点 | 超阈值记录 WARN |
| 换手率绝对差 | `<= 0.05` 个百分点 | 超阈值记录 WARN |
| 实时时间戳差 | `<= 30` 秒 | 超阈值记录 WARN |

## FAIL 条件

- 源返回空表且无法比较目标字段。
- 缺少任务013要求的关键字段。
- `date` 或 `code` 无法与目标集合对齐。
- 关键数值字段无法转为数值。
- 价格字段出现异常 0 值。
- `adata` 被加入 `full_realtime_quotes` 或 `realtime_quotes` 默认策略。
- `adata` adapter 对外暴露 full realtime 能力。

## WARN 条件

- 单位比例差异可解释，例如 AKShare 历史成交量按“手”返回、baostock 按“股”返回时记录 `scale=100`。
- `pct_chg` 因来源算法、复权/除权处理或四舍五入口径不同而超阈值。
- 交易日集合存在差异，但不自动修正。
- 指数实时成交量在不同源之间存在单位比例差异。

## 不变原则

- 不用一个源覆盖另一个源。
- 不为通过一致性校验而修改原始数据。
- 不把 lite realtime 升级为 full realtime。
- 不把 WARN 转化为交易含义。
