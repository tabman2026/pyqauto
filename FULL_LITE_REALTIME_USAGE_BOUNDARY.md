# FULL_LITE_REALTIME_USAGE_BOUNDARY

生成时间：2026-06-12

任务013冻结 `full_realtime_quotes` 与 `lite_realtime_quotes` 的使用边界。本边界用于数据源路由、字段质量检查和后续 S0 只读沙盒前置判断，不包含任何交易建议或自动交易逻辑。

## 默认策略

```text
full_realtime_quotes:  easyquotation_sina -> easyquotation_tencent
lite_realtime_quotes:  adata
```

## full_realtime_quotes

`full_realtime_quotes` 必须提供完整盘中字段：

```text
code, name, last_price, pre_close, open, high, low, volume, amount, pct_chg
```

允许用途：

- 完整实时行情字段观察。
- 需要 `open/high/low/pre_close` 的实时字段校验。
- full realtime 主备源一致性报警。

禁止事项：

- 禁止用 lite 源补齐 full 字段。
- 禁止用人工猜测填补 `open/high/low/pre_close`。
- 禁止把缺字段源继续作为 full 默认源。

## lite_realtime_quotes

`lite_realtime_quotes` 只要求轻量字段：

```text
code, name, last_price, volume, amount, pct_chg
```

允许用途：

- 轻量价格观察。
- 源健康探针。
- 可用性补充。

禁止用途：

- 不得进入 `full_realtime_quotes`。
- 不得用于需要 `open/high/low/pre_close` 的盘中逻辑。
- 不得用于涨跌幅精确校验主源。
- 不得直接喂给 S0 full realtime 字段。
- 不得作为 full realtime fallback。

## adata 边界裁决

任务013已在代码和策略两层冻结 adata 边界：

- `DEFAULT_SOURCE_POLICY["lite_realtime_quotes"] == ["adata"]`。
- `DEFAULT_SOURCE_POLICY["full_realtime_quotes"]` 不包含 `adata`。
- `DEFAULT_SOURCE_POLICY["realtime_quotes"]` 不包含 `adata`。
- `ADataAdapter.supported_features` 不再包含 `full_realtime_quotes` 或 `realtime_quotes`。
- 直接调用 `ADataAdapter.fetch_full_realtime_quotes()` 返回 `UnsupportedFeatureError`。
- live 一致性校验中 `adata lite_realtime_quotes` 返回 2 行，字段为 lite 字段集合。

## 后续约束

后续任务如需调整 adata 角色，必须先重新运行字段标准化测试、full/lite 质量闸门测试和 live 一致性校验。未通过前，不得把 adata 放入 full realtime 默认链路。
