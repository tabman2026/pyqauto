# ENVIRONMENT

本项目的生产候选验收使用项目自带虚拟环境，而不是系统默认 `python`。

原因：

1. 同一台机器可能同时安装多个 Python 版本。
2. 系统默认 `python` 可能缺少 `pytest`、`ruff`、`pandas` 等开发依赖。
3. 项目级 `.venv` 能隔离依赖并提高验收可复现性。
4. 默认 `python -X utf8 -m pytest -q` 如果只因为缺少 `pytest` 失败，应判定为环境未初始化，不应判定为代码层失败。

## Windows

初始化开发环境：

```bat
scripts\setup_dev_windows.bat
```

脚本行为：

1. 保留 `chcp 65001 >nul`。
2. 优先使用 `py -3.10 -X utf8 -m venv .venv` 创建虚拟环境。
3. 如果 `py -3.10` 不可用，尝试 `C:\python\python.exe -X utf8 -m venv .venv`。
4. 如果仍失败，提示安装 Python 3.10+，不静默失败。
5. 使用 `.venv\Scripts\python.exe -X utf8` 安装 `pip setuptools wheel` 和 `.[dev]`。

运行本地验收：

```bat
scripts\run_tests_windows.bat
```

等价核心命令：

```bat
.venv\Scripts\python.exe -X utf8 -m pytest -q
.venv\Scripts\python.exe -X utf8 -m compileall -q astock_source_router tests examples
.venv\Scripts\python.exe -X utf8 scripts\smoke_test_offline.py
.venv\Scripts\python.exe -X utf8 scripts\doctor_env.py
```

如已安装 ruff，脚本还会执行：

```bat
.venv\Scripts\python.exe -X utf8 -m ruff check .
```

ruff 未安装时记录 `SKIP`，不单独导致生产候选失败。

## macOS / Linux

初始化开发环境：

```bash
bash scripts/setup_dev_macos.sh
```

运行本地验收：

```bash
bash scripts/run_tests_macos.sh
```

等价核心命令：

```bash
.venv/bin/python -X utf8 -m pytest -q
.venv/bin/python -X utf8 -m compileall -q astock_source_router tests examples
.venv/bin/python -X utf8 scripts/smoke_test_offline.py
.venv/bin/python -X utf8 scripts/doctor_env.py
```

## 环境诊断

`scripts/doctor_env.py` 会检查并输出：

- 当前 Python 路径和版本。
- 是否在虚拟环境中。
- `pytest`、`ruff`、`pandas`、`astock_source_router` 是否可导入。
- 当前工作目录。
- 操作系统。
- UTF-8 模式状态。

诊断报告写入：

```text
logs/environment_report.json
```

JSON 使用 UTF-8 写入，并保留 `ensure_ascii=False`。

## 网络边界

环境初始化安装依赖时需要访问 Python 包索引。默认测试、compileall、离线 smoke test 和 doctor_env 不依赖联网。

真实源 smoke test 仍必须显式启用：

```bash
ENABLE_LIVE_SMOKE_TEST=1 .venv/bin/python -X utf8 scripts/smoke_test_live.py
```

Windows PowerShell：

```powershell
$env:ENABLE_LIVE_SMOKE_TEST="1"
.venv\Scripts\python.exe -X utf8 scripts\smoke_test_live.py
```
