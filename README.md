# aquote-router

本项目不提供投资建议，不生成候选股池，不生成买卖点，不接入真实交易。

`aquote-router` 是一个面向 A 股量化研究的轻量行情源路由器，提供 pytdx 服务器池、主备切换、easyquotation 兜底、统一返回模型、source policy 和 JSONL / SQLite 审计追踪。

## 功能

- pytdx 服务器池读取，按 `primary -> hot_backup -> backup` 路由。
- 同级 pytdx 服务器按 `latency_ms` 升序选择。
- `realtime_quotes`、`full_realtime_quotes`、`index_realtime` 支持 pytdx 失败后切换到 `easyquotation_sina -> easyquotation_tencent`。
- `minute_kline` 保持 pytdx-only，所有 pytdx 源失败时抛出明确异常。
- 统一 `QuoteRecord` 返回模型，包含 `source`、`source_level`、`is_fallback`、`fallback_from`、`trace_id`。
- JSONL 和 SQLite 双审计，记录每次调用的来源尝试、耗时、结果和错误。
- 提供 Python API、CLI、示例、单元测试、CI 和发布工作流。

## 不做什么

- 不提供投资建议。
- 不生成候选股池。
- 不生成买卖点。
- 不接入真实交易。
- 不保存账号、登录态、密钥或 webhook。
- 不做行情 API 服务端或数据再分发服务。

## 安装

```bash
python -X utf8 -m pip install aquote-router
```

本地开发：

```bash
python -X utf8 -m pip install -e ".[dev,test]"
```

## 快速开始

```python
from aquote_router import QuoteRouter

router = QuoteRouter.from_config(
    pytdx_servers_path="config/pytdx_servers.example.json",
    source_policy_path="config/source_policy.example.yaml",
    audit_jsonl_path="logs/aquote_router_audit.jsonl",
    audit_sqlite_path="logs/aquote_router_audit.sqlite3",
)

records = router.realtime_quotes(["000001", "600000"])
for record in records:
    print(record.to_dict())
```

公开示例 pytdx 服务器可用性会变化，用户应维护自己的服务器池配置。不要把生产配置、账号信息或本地绝对路径提交到仓库。

## 公共 API

```python
router.realtime_quotes(["000001", "600000"])
router.full_realtime_quotes(["000001", "600000"])
router.index_realtime(["000001", "399001"])
router.minute_kline("000001", period="1m")
```

## CLI

```bash
aquote-router diagnose
aquote-router realtime 000001 600000
aquote-router full-realtime 000001 600000
aquote-router index 000001 399001
aquote-router minute 000001 --period 1m
```

常用选项：

```bash
aquote-router --json diagnose
aquote-router --config config/source_policy.example.yaml realtime 000001
aquote-router --audit-jsonl logs/audit.jsonl --audit-sqlite logs/audit.sqlite3 realtime 000001
```

失败时 CLI 返回非 0 exit code，并输出简洁错误信息。

## Source Policy

`config/source_policy.example.yaml` 定义每个 API 的来源顺序：

- `realtime_quotes`：`pytdx -> easyquotation_sina -> easyquotation_tencent`
- `full_realtime_quotes`：`pytdx -> easyquotation_sina -> easyquotation_tencent`
- `index_realtime`：`pytdx -> easyquotation_sina -> easyquotation_tencent`
- `minute_kline`：`pytdx`

pytdx 内部会按 `primary -> hot_backup -> backup` 选择；同级按 `latency_ms` 升序。

## 审计

每次调用都会生成同一个 `trace_id`，并记录：

- `api_name`
- `symbols`
- `started_at` / `finished_at` / `duration_ms`
- `selected_source` / `selected_source_level`
- `attempts`
- `fallback_chain`
- `success`
- `error_type` / `error_message`
- `record_count`

详见 [docs/AUDIT_TRAIL.md](docs/AUDIT_TRAIL.md)。

## Fallback 示例

如果 `realtime_quotes` 的 pytdx primary 和 hot_backup 都失败，backup 成功，则记录：

```text
selected_source=pytdx
selected_source_level=backup
fallback_chain=["pytdx:primary", "pytdx:hot_backup"]
is_fallback=True
fallback_from=pytdx:hot_backup
```

如果所有 pytdx 源失败，路由继续尝试 `easyquotation_sina`，再尝试 `easyquotation_tencent`。

## 为什么 minute_kline 是 pytdx-only

分钟 K 线对字段语义、时间粒度和数据完整性更敏感。第一版只允许 pytdx 提供 `minute_kline`，避免跨来源混用导致不可解释的差异。所有 pytdx 源失败时，库会抛出结构化异常并写入审计记录，不会伪造数据。

## 与常见库的关系

- AKShare：覆盖面广，适合直接获取多类金融数据；本项目只做行情来源路由和审计。
- efinance：可作为用户侧数据工具；本项目第一版不内置为默认来源。
- easyquotation：本项目通过它作为 realtime 兜底来源。
- pytdx：本项目的主行情来源和分钟 K 线来源。

## 贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。新增真实数据源前，必须先提交 adapter 单元测试和字段标准化测试。默认测试不得联网，真实来源 smoke test 必须显式启用。

## Issue 反馈

请使用 GitHub issue 模板提交：

- Bug report
- Adapter request
- Data source failure

报告来源失败时，请提供 API 名称、symbol、时间、配置片段和审计 trace_id。请不要粘贴账号信息或私有配置。

## 风险免责声明

本项目仅用于研究基础设施。行情来源可能延迟、中断或返回异常字段。用户应自行校验数据质量，并遵守数据来源的服务条款和适用法规。

## License

MIT License. See [LICENSE](LICENSE).
