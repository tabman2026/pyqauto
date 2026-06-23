# TASK028 FINAL REPORT

## 结论

Task028 已完成。项目新增 L6 Autonomous Control Layer，用于行情源路由的
self-healing、self-recovery 和 self-stabilizing data infrastructure。

## 已实现

- 新增 `astock_source_router/autonomy/`：
  - `recovery_engine.py`
  - `anomaly_detector.py`
  - `decay_model.py`
  - `self_healing.py`
- 新增 `pyqauto/autonomy/` 兼容命名空间。
- `MarketRouter` 新增：
  - `router.autonomy_status()`
  - `router.recovery_state()`
  - `router.anomaly_report()`
  - `router.source_weight_decay()`
- 实现 source failure 降级、成功恢复 `NORMAL`。
- 实现 schema drift 降低后的 unblock。
- 实现 `score = old * 0.9 + new * 0.1` 衰减模型。
- 实现 sudden full failure、temporary instability 和 observation window。

## 安全边界

本任务未新增交易系统、策略/预测、投资建议、QMT、券商、自动交易、选股或收益预测。
source policy 默认链路未修改，字段标准未修改，审计日志结构未修改。

## 验收记录

新增测试：

- `tests/test_autonomy_recovery.py`
- `tests/test_anomaly_detection.py`
- `tests/test_decay_model.py`
- `tests/test_self_healing_integration.py`

验收命令以实际运行输出为准：

```powershell
chcp 65001 | Out-Null
python -X utf8 -m pytest -q
python -X utf8 -m ruff check .
python -X utf8 scripts/check_release.py
python -X utf8 scripts/smoke_test.py
python -X utf8 -m build
```

## 审计结论

L6 仅做数据源稳定性控制和运行时状态学习，不改变 governance / graph 核心逻辑，
不改变默认 source policy，不返回未通过质量校验的数据，不产生任何交易行为。
