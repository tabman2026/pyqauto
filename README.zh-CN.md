# pyqauto 中文快速开始

pyqauto 是一个面向 A 股量化研究和数据验证脚本的轻量行情源路由器。它把 pytdx 主备切换、easyquotation Sina/Tencent fallback、实时行情、分钟K线、15分钟K线、日K、统一 `kline` 接口、source policy、JSONL / SQLite 行情审计和 `trace_id` 串在一起，帮助你在本地研究环境里更清楚地知道每次 A股行情 调用用了哪个数据源。

## 项目是什么

本项目是一个 Python 包，包名是 `pyqauto`，导入名是 `pyqauto`。它不生产行情数据，只调用公开 Python 依赖的公开接口，并把 A股实时行情、A股K线、分钟K线和日K 返回为统一的数据对象。

## 解决什么问题

公开免费行情源会因为网络、地区、时段、上游结构变化而失败。pyqauto 把 source policy、pytdx server 主备顺序、easyquotation fallback、返回字段和审计日志放在一个入口里，减少每个研究脚本重复处理数据源 fallback 的成本。

## 不做什么

本项目不提供投资建议，不接入下单或执行系统，不保证公开免费行情源 100% 准确、实时、完整、可用。

它也不生产行情数据、不对外再分发行情数据、不绕过上游限制、不保存账号登录态、不提供自动化下单能力。

## 安装

Windows 终端建议先切换 UTF-8：

```bat
chcp 65001 >nul
```

安装 PyPI 版本：

```bash
python -X utf8 -m pip install pyqauto -i https://pypi.org/simple
```

## 30 秒获取实时行情

```python
import pyqauto as aq

items = aq.quotes(["000001", "600000"])
for item in items:
    print(item.symbol, item.price, item.source, item.source_level, item.trace_id)
```

`source` 会显示返回记录的数据源，例如 `pytdx`、`easyquotation_sina` 或 `easyquotation_tencent`。`source_level` 用于 pytdx 主备角色，`trace_id` 用于把返回记录和 JSONL / SQLite 审计日志对应起来。

## 30 秒获取 15分钟K线

```python
bars = aq.kline("000001", period="15m", count=120)
for bar in bars[:5]:
    print(bar.datetime, bar.open, bar.high, bar.low, bar.close, bar.source)
```

15分钟K线 通过 pytdx 获取。K线接口不会使用 easyquotation fallback，也不会伪造 K线。

## 30 秒获取日K

```python
daily = aq.daily("000001", count=120)
for bar in daily[:5]:
    print(bar.datetime, bar.open, bar.high, bar.low, bar.close, bar.source)
```

也可以使用统一接口：

```python
daily = aq.kline("000001", period="1d", count=120)
```

## K线超时怎么办

K线目前是 pytdx-only。免费 pytdx server 会随网络、地区和时间变化；如果 A股K线、分钟K线、15分钟K线 或日K超时，先从当前网络探测可用 server：

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

然后显式传入本地探测结果：

```bash
pyqauto kline 000001 --period 15m --count 10 --pytdx-servers config/pytdx_servers.active.local.json --json
```

`config/pytdx_servers.active.local.json` 是本地诊断结果，不应提交到仓库。

## 如何运行 probe-pytdx

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

常用参数：

- `--timeout 3.0`：单个 server 探测超时时间。
- `--limit 20`：只探测前 20 个候选，`0` 表示不限制。
- `--symbol 000001`：用于探测的股票代码。
- `--minute-period 15m`：用于分钟K线探测的周期。
- `--count 10`：用于 K线探测的条数。

## 如何运行 source schema live probe

```bash
pyqauto source-schema-probe-live --json
pyqauto source-schema-probe-live --symbols 000001 600000 --json
```

该命令会连接上游公开源，检查 raw 字段是否仍能标准化为 pyqauto public
records。`WARN` 表示至少一个源通过、另一个源不可用或被 schema 校验拒绝；
`FAIL` 表示没有源通过，CLI 会返回非 0。未通过校验的行只写入
`rejected_reason`、`schema_drift_fields` 或 `error_message`，不会进入 public
records。

AkShare `成交量` 按手转股，`成交额` 保持元；Tencent
`价格/成交量(手)/成交额` 会解析成交量和成交额后再校验。更多细节见
[docs/SOURCE_SCHEMA_LIVE_PROBE.md](docs/SOURCE_SCHEMA_LIVE_PROBE.md)。

## 如何查看 source / source_level / trace_id

Python 对象可直接读取字段：

```python
item = aq.quote("000001")
print(item.source, item.source_level, item.trace_id)
```

CLI 建议加 `--json`：

```bash
pyqauto realtime 000001 --json
pyqauto kline 000001 --period 15m --count 10 --json
```

如果启用审计日志，使用同一个 `trace_id` 可以定位对应请求：

```python
aq.configure(
    audit_jsonl_path="logs/pyqauto_audit.jsonl",
    audit_sqlite_path="logs/pyqauto_audit.sqlite3",
)
```

## 数据源说明

默认数据源包括：

- `pytdx`：实时行情和全部 K线接口的主数据源。
- `easyquotation_sina`：实时行情 fallback，底层为 easyquotation 的 Sina 通道。
- `easyquotation_tencent`：实时行情 fallback，底层为 easyquotation 的 Tencent 通道。

更多细节见 [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)。

## fallback 规则

默认实时行情 fallback：

```text
realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent
full_realtime_quotes: pytdx -> easyquotation_sina -> easyquotation_tencent
index_realtime: pytdx -> easyquotation_sina -> easyquotation_tencent
```

默认 K线规则：

```text
minute_kline: pytdx only
daily_kline: pytdx only
kline: pytdx only
```

实时行情可以按 source policy 从 pytdx fallback 到 easyquotation Sina/Tencent。K线接口不使用 easyquotation fallback；如果 pytdx 全部失败，会抛出结构化错误并写入审计记录。

## 审计日志说明

每次路由调用都会生成 `trace_id`。启用 JSONL 或 SQLite 后，审计日志会记录：

- `api_name`
- `symbols`
- `selected_source`
- `selected_source_level`
- `attempts`
- `fallback_chain`
- `duration_ms`
- `record_count`
- `success`
- `error_type`
- `error_message`

审计日志适合排查数据源 fallback、pytdx server 失败、行情源路由结果和上游变化。更多细节见 [docs/AUDIT_TRAIL.md](docs/AUDIT_TRAIL.md)。

## CLI 常用命令

```bash
pyqauto diagnose --json
pyqauto realtime 000001 600000 --json
pyqauto full 000001 600000 --json
pyqauto index 000001 399001 --json
pyqauto minute 000001 --period 15m --count 120 --json
pyqauto daily 000001 --count 120 --json
pyqauto kline 000001 --period 15m --count 120 --json
pyqauto kline 000001 --period 1d --count 120 --json
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

## 常见问题入口

- 新手入口：[docs/NEW_USER_START_HERE.md](docs/NEW_USER_START_HERE.md)
- K线使用指南：[docs/KLINE_GUIDE.md](docs/KLINE_GUIDE.md)
- 数据源说明：[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)
- CLI 说明：[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)
- 常见问题排查：[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- 错误码：[docs/ERROR_CODES.md](docs/ERROR_CODES.md)
- Issue 反馈指南：[docs/ISSUE_GUIDE.md](docs/ISSUE_GUIDE.md)

## 开发者入口

- 新手开发指南：[docs/BEGINNER_DEVELOPER_GUIDE.md](docs/BEGINNER_DEVELOPER_GUIDE.md)
- 上游共性研究：[docs/UPSTREAM_COMMONS_RESEARCH.md](docs/UPSTREAM_COMMONS_RESEARCH.md)
- Adapter 模板：[docs/ADAPTER_TEMPLATE.md](docs/ADAPTER_TEMPLATE.md)
- 字段映射模板：[docs/FIELD_MAPPING_TEMPLATE.md](docs/FIELD_MAPPING_TEMPLATE.md)
- 单位规则：[docs/UNIT_RULES_FOR_ADAPTERS.md](docs/UNIT_RULES_FOR_ADAPTERS.md)
- 什么时候发版本：[docs/WHEN_TO_RELEASE.md](docs/WHEN_TO_RELEASE.md)
- v0.4.0 adapter 候选评审入口：
  [评审](docs/ADAPTER_CANDIDATE_REVIEW_V040.md)、
  [字段映射草案](docs/ADAPTER_FIELD_MAPPING_DRAFT_V040.md)、
  [单位规则草案](docs/ADAPTER_UNIT_RULES_DRAFT_V040.md)、
  [source policy 草案](docs/SOURCE_POLICY_DRAFT_V040.md)。
- v0.4.0 candidate normalize 合同：
  [CANDIDATE_NORMALIZE_CONTRACT_V040.md](docs/CANDIDATE_NORMALIZE_CONTRACT_V040.md)
  和
  [V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md](docs/V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md)。
  这些只是候选 adapter 评审文档，candidate normalizers are test-only
  contracts, not public adapter APIs。These drafts do not mean the current version supports these data sources。
  候选源 do not enter the default fallback chain。

## Issue 反馈方式

提交 issue 前请先运行：

```bash
pyqauto diagnose --json
```

如果是 K线超时或 pytdx 连接失败，请再运行：

```bash
pyqauto probe-pytdx --json --output config/pytdx_servers.active.local.json
```

反馈时建议提供：

- Python 版本、操作系统和 pyqauto 版本。
- 使用的命令或最小 Python 代码。
- `trace_id`、结构化错误码和已脱敏的审计片段。
- 是否只在某个网络、地区或时段失败。

不要提交本地 active pool、完整日志文件、SQLite 文件或本机绝对路径。

## 免责声明

本项目仅用于本地研究和工程验证场景中的行情源路由与审计追踪。本项目不提供投资建议，不接入下单或执行系统，不保证公开免费行情源 100% 准确、实时、完整、可用。使用者需要自行验证数据质量，并遵守各上游项目和数据源的使用条款。

## License

MIT License. See [LICENSE](LICENSE).
