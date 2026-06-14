# Open Source Release Report

## Task 015.2 Result

- Completion: yes
- Package name: `aquote-router`
- Import name: `aquote_router`
- Version: `0.1.0`
- Git CLI available: yes, `git version 2.54.0.windows.1`
- GitHub CLI available: yes, `gh version 2.94.0`
- GitHub CLI authentication recovered: yes
- GitHub account: `tabman2026`
- Git operations protocol: HTTPS
- Public repository: `https://github.com/tabman2026/aquote-router`
- Repository visibility: public
- Repository description and topics: configured
- Main branch push: completed
- Release tag push: `v0.1.0` completed
- GitHub Release: completed
- GitHub Release URL: `https://github.com/tabman2026/aquote-router/releases/tag/v0.1.0`
- GitHub Actions check: completed
- CI status: success on `main` and `v0.1.0`
- Publish workflow status: failed at PyPI Trusted Publishing exchange with `invalid-publisher`
- PyPI actual publish: not completed
- PyPI publish blocker: PyPI Trusted Publisher is not configured for `tabman2026/aquote-router`, workflow `publish.yml`, environment `pypi`.

## Required Checks

1. 是否 gh 认证恢复：是
2. GitHub 登录账号：`tabman2026`
3. 是否通过 pytest：是
4. 是否通过防泄漏扫描：是
5. 是否通过 smoke test：是
6. 是否通过 build：是
7. 是否完成 GitHub public repo 创建：是
8. GitHub 仓库 URL：`https://github.com/tabman2026/aquote-router`
9. 是否完成 main push：是
10. 是否完成 `v0.1.0` tag push：是
11. 是否完成 GitHub Release：是
12. GitHub Release URL：`https://github.com/tabman2026/aquote-router/releases/tag/v0.1.0`
13. 是否完成 GitHub Actions 检查：是
14. CI 状态：CI 成功；Publish 失败，原因为 PyPI Trusted Publishing `invalid-publisher`
15. 是否完成 PyPI publish workflow 检查：是
16. 是否实际完成 PyPI 发布：否
17. PyPI 未发布原因：PyPI 项目后台尚未配置匹配的 Trusted Publisher。
18. 是否存在越界输出：否
19. 是否包含投资建议：否
20. 是否包含交易执行代码：否

## PyPI Workflow Review

- Uses `pypa/gh-action-pypi-publish`: yes
- Includes `permissions: id-token: write`: yes
- Uses environment `pypi`: yes
- Workflow does not contain `PYPI_TOKEN`.
- Workflow does not contain `username` / `password` credentials.
- Workflow does not create `.pypirc`.
- Repository `.pypirc` file: not present

## Boundary Review

- 是否包含 QMT / 券商 / 真实交易：否
- 是否包含买卖点 / 候选股池 / 收益率 / 胜率：否
- 是否包含 cookie、token、账号登录态：否
- 不输出投资建议、仓位建议、收益率承诺、自动交易逻辑。
- 是否扩大开源范围：否

## Commands Run

1. `python -X utf8 -m pytest -q`
2. `python -X utf8 scripts/check_release.py`
3. `python -X utf8 scripts/smoke_test.py`
4. `python -X utf8 -m build`
5. `git status`
6. `git branch --show-current`
7. `git log --oneline -5`
8. `git tag`
9. `git remote -v`
10. `gh auth status -h github.com`
11. `gh repo view tabman2026/aquote-router`
12. `gh repo create aquote-router --public --description "..."`
13. `git remote add origin https://github.com/tabman2026/aquote-router.git`
14. `gh repo edit tabman2026/aquote-router --description "..." --add-topic ...`
15. `git push -u origin main`
16. `git push origin v0.1.0`
17. `gh release view v0.1.0 --repo tabman2026/aquote-router`
18. `gh release create v0.1.0 --repo tabman2026/aquote-router --title "aquote-router v0.1.0" --notes-file CHANGELOG.md`
19. `gh run list --repo tabman2026/aquote-router --limit 10`
20. `gh run view 27504819866 --repo tabman2026/aquote-router --log-failed`

## Manual Next Steps

1. In PyPI, configure Trusted Publishing for project `aquote-router` with owner `tabman2026`, repository `aquote-router`, workflow `publish.yml`, and environment `pypi`.
2. After PyPI Trusted Publishing is configured, rerun the GitHub Publish workflow or push a new release tag.
