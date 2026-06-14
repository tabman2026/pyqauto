# Open Source Release Report

## Summary

- Independent open-source directory: yes
- Package name: `aquote-router`
- Import name: `aquote_router`
- Version: `0.1.0`
- License: MIT
- Local test status: passed
- Release scan status: passed
- Build status: passed
- Windows acceptance status: passed
- Local git commit: completed through Dulwich because Git CLI is unavailable
- Release tag: `v0.1.0`
- GitHub repository creation: not completed because GitHub CLI is unavailable
- GitHub push: not completed because no remote repository exists locally
- GitHub Release: not completed because GitHub CLI is unavailable
- PyPI workflow: generated with Trusted Publishing
- PyPI actual publish: not completed

## Required Checks

1. 是否完成独立开源目录：是
2. 是否生成 pyproject.toml：是
3. 是否生成 README：是
4. 是否生成 LICENSE：是
5. 是否生成 GitHub Actions：是
6. 是否生成 issue 模板：是
7. 是否通过 pytest：是
8. 是否通过防泄漏扫描：是
9. 是否完成 git commit：是
10. 是否完成 GitHub 仓库创建：否
11. 是否完成 GitHub push：否
12. 是否完成 release tag：是
13. 是否完成 GitHub Release：否
14. 是否完成 PyPI Trusted Publishing 配置文件：是
15. 是否实际发布 PyPI：否
16. PyPI 未发布阻断原因：无法在本机确认 GitHub 仓库和 PyPI Trusted Publishing 配置
17. 下一步人工动作：创建 GitHub 仓库、添加 remote、push main 和 tag、配置 PyPI Trusted Publishing
18. 是否存在越界输出：否
19. 是否包含投资建议：否
20. 是否包含交易执行代码：否

## Boundary Review

- 是否包含 QMT / 券商 / 真实交易：否
- 是否包含买卖点 / 候选股池 / 收益率 / 胜率：否
- 是否包含账号、登录态、webhook 或密钥：否
- 是否包含本地绝对路径：否

## Validation Commands

1. `python -X utf8 -m pytest -q`
2. `python -X utf8 scripts/check_release.py`
3. `python -X utf8 scripts/smoke_test.py`
4. `python -X utf8 -m build`
5. `scripts\windows_acceptance.bat`

## Manual Next Steps

1. Follow `MANUAL_GITHUB_PUBLISH_STEPS.md` to create and push the public GitHub repository.
2. Follow `PYPI_TRUSTED_PUBLISHING_SETUP.md` to configure PyPI Trusted Publishing.
3. After GitHub remote is configured, push `main` and `v0.1.0`.
4. Create the GitHub Release from `CHANGELOG.md`.
