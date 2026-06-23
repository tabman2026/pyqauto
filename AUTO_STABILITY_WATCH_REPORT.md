# AUTO STABILITY WATCH REPORT

生成时间：2026-06-12

## 结论

任务014B已新增本地自动稳定性观察脚本和 Windows 定时任务脚本。本轮最终 live 观察已通过：

| 项目 | 结果 |
|---|---:|
| 运行入口 | `scripts/run_stability_watch_windows.bat` |
| 显式环境变量 | `ENABLE_STABILITY_WATCH=1` |
| 是否由定时任务触发 | 否，本次为手动运行 bat |
| 交易日过滤 | PASS，2026-06-12 为交易日 |
| 是否计入 5 日观察 | 是 |
| `daily_acceptance` | PASS |
| `overall_live_gate` | PASS |
| `source_consistency` | WARN，无 FAIL |
| pytdx 可用服务器 | 34 |
| pytdx primary | `58.63.254.191:7709` |
| pytdx hot backup | `183.60.224.177:7709` |
| `single_server_warning` | False |
| `server_pool_ready` | True |
| easyquotation fallback | PASS |
| AKShare daily/calendar | PASS / PASS |
| Baostock daily/calendar | PASS / PASS |
| adata lite 边界 | PASS |
| 审计日志写入 | PASS |

## Windows 定时任务

| 项目 | 结果 |
|---|---|
| 安装脚本 | `scripts/install_stability_watch_task_windows.bat` |
| 卸载脚本 | `scripts/uninstall_stability_watch_task_windows.bat` |
| 任务名 | `A股行情源路由器_稳定性观察` |
| 计划 | 每天 15:40 |
| 执行目标 | `scripts\run_stability_watch_windows.bat --scheduled` |
| 当前安装状态 | 已安装 |

安装脚本使用当前项目绝对路径创建任务，避免计划任务工作目录错误。卸载脚本只删除计划任务，不删除日志或报告。

## 同日重跑记录

本轮稳定性观察曾两次因 Baostock `trade_calendar` 20 秒源级超时导致 `daily_acceptance=FAIL`；随后将稳定性观察内部 live source timeout 提高到 45 秒后重跑通过。失败记录已保留在 `logs/stability_daily_20260612.json` 的 `same_day_previous_runs`。

未出现 `WinError 10013` / `PermissionError` / `Access is denied`，`local_network_permission_error.present=False`。

## 输出文件

```text
logs/stability_daily_20260612.json
reports/STABILITY_DAILY_20260612.md
logs/stability_5day_summary.json
STABILITY_5DAY_SUMMARY.md
```

## 禁止项审计

- 是否生成候选股池：否
- 是否生成策略信号：否
- 是否生成买点：否
- 是否生成卖点：否
- 是否生成仓位：否
- 是否生成收益率：否
- 是否生成胜率：否
- 是否生成交易计划：否
- 是否接入 QMT：否
- 是否接入券商账户：否
- 是否自动下单：否
- 是否自动交易：否

本报告只用于行情源稳定性观察，不构成交易建议。
