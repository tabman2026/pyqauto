# CURRENT_BASELINE

生成时间：2026-06-11

## 一、当前项目结构

```text
astock_source_router/
  __init__.py
  adapters/
    adata_adapter.py
    akshare_adapter.py
    baostock_adapter.py
    easyquotation_adapter.py
    efinance_adapter.py
    fake_adapter.py
    mootdx_adapter.py
  core/
    adapter_base.py
    audit_logger.py
    cache.py
    circuit_breaker.py
    errors.py
    features.py
    health_score.py
    models.py
    policy.py
    rate_limiter.py
    registry.py
    router.py
    schema.py
examples/
  demo_daily_kline.py
  demo_realtime.py
  demo_source_health.py
scripts/
  run_tests_macos.sh
  run_tests_windows.bat
tests/
  conftest.py
  test_audit_logger.py
  test_cache.py
  test_fallback.py
  test_quality_and_circuit.py
  test_router_basic.py
  test_schema.py
```

当前包名为 `astock_source_router`，项目中文定位为“A股多源行情路由器”。现有核心架构包括 `MarketRouter`、字段级 `SourcePolicy`、fallback、`HealthScoreBoard`、`CircuitBreaker`、`AuditLogger`、adapter 机制、TTL 缓存和基础字段标准化。

## 二、当前测试结果

已执行命令：

```bash
python -X utf8 -m pytest -q
```

结果：失败。当前默认 `python` 指向 `C:\Python314\python.exe`，该环境未安装 `pytest`。

```text
C:\Python314\python.exe: No module named pytest
```

已执行命令：

```bash
python -X utf8 -m compileall -q astock_source_router tests examples
```

结果：通过。

备用解释器补跑：

```bash
C:\python\python.exe -X utf8 -m pytest -q
C:\python\python.exe -X utf8 -m compileall -q astock_source_router tests examples
```

结果：通过，`9 passed`；存在一条 pandas / numpy DeprecationWarning，不影响当前测试结果。

已执行命令：

```bash
python -X utf8 -m ruff check .
```

结果：未执行成功。默认 Python 环境未安装 `ruff`。

## 三、当前风险点

1. 默认解释器缺少 dev 依赖，导致指定的 `python -X utf8 -m pytest -q` 无法直接运行。
2. 标准字段尚未包含生产化要求中的 `data_timestamp`。
3. 质量闸门当前主要识别空 DataFrame 和字段缺失，尚未完整覆盖字段类型错误、目标日期异常、价格/成交额为 0、行数不足、实时数据过期、HTML / 验证码 / 风控页面等情况。
4. SQLite 审计表当前只有 `source_request_log` 和 `source_fallback_trace`，缺少 `source_health_score`、`source_quality_check`、`source_failure_event`。
5. 审计字段当前使用 `feature`，尚未同时提供生产化要求中的 `function_name`、`target`、`attempted_sources`、`fallback_reason`、`field_missing`。
6. 尚无 `data_usage_guard.py`，历史回测和盘中使用权限缺少统一记录。
7. smoke test 脚本缺失，真实源启用开关和离线 smoke test 尚未建立。
8. 测试矩阵覆盖不足，缺少独立的 daily kline、realtime quotes、health score、circuit breaker、quality gate、data usage guard、UTF-8 输出等测试文件。
9. 脚本命令尚未完全匹配最终验收要求，Windows bat 的 `chcp 65001 >nul` 格式需要统一。

## 四、当前可生产化缺口

1. 完整字段标准化和质量闸门。
2. 请求级完整审计、fallback trace、质量检查、失败事件、健康评分持久化。
3. 真实源 smoke test 框架，且默认不联网。
4. 未来函数防火墙，用于区分 `intraday`、`after_close`、`backtest` 数据使用模式。
5. 更完整的离线测试矩阵。
6. 文档边界冻结和生产候选验收清单。

## 五、不允许改动的边界

1. 不改 Python 包名：必须保持 `astock_source_router`。
2. 不推倒重写现有架构，保留 `MarketRouter`、字段级 source policy、fallback、health score、circuit breaker、audit logger、adapter 机制。
3. 不复制第三方行情库核心代码，只调用公开 API。
4. 不内置 cookie、token、账号、券商登录态、QMT、同花顺客户端登录态。
5. 不输出买卖建议、候选股池、策略信号、交易计划、仓位建议、收益率预测或自动交易能力。
6. 默认测试不联网；真实源测试必须通过 `ENABLE_LIVE_SMOKE_TEST=1` 显式启用。
7. 不做高频抓取，不做行情数据对外再分发服务。
8. efinance、mootdx、Ashare 等维护或边界不确定的数据源只能作为 optional adapter，不作为默认强依赖。
9. 所有文本、JSON、CSV、SQLite 日志读写必须显式 UTF-8；JSON / JSONL 中文输出使用 `ensure_ascii=False`。
