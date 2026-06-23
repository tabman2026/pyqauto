# AGENTS.md

后续由 Codex / 自动化助手维护本项目时，必须遵守：

1. 所有 Python 文件使用 UTF-8。
2. Windows 运行脚本必须先执行 `chcp 65001`，Python 使用 `python -X utf8` 或设置 `PYTHONUTF8=1`。
3. 所有文本、JSON、CSV、SQLite 日志写入必须显式使用 UTF-8。
4. 不复制第三方行情库核心代码，只调用公开 API。
5. 不内置 cookie、token、账号、券商登录态。
6. 不输出买卖建议、仓位建议、收益率承诺、自动交易逻辑。
7. 每个任务必须保留审计结论和验收结果。
8. 新增真实数据源前，必须先写 adapter 单元测试和字段标准化测试。
9. 任何影响 source policy、字段标准、审计日志结构的修改，必须更新 README / SOURCE_POLICY / PROJECT_STATE。
10. 默认测试不得联网；真实源 smoke test 必须通过 `ENABLE_LIVE_SMOKE_TEST=1` 显式启用。
11. efinance、mootdx、Ashare 等维护或边界不确定的数据源只能作为 optional adapter。
12. 不把本项目改造成行情 API 服务端或数据再分发服务。
13. 修改 Windows 脚本时必须保留 `chcp 65001 >nul`。
14. 修改 JSON / JSONL 输出时必须保留 `ensure_ascii=False`。
