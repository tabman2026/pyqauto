# Release Checklist

## Local Validation

```bash
python -X utf8 -m pytest -q
python -X utf8 scripts/check_release.py
python -X utf8 scripts/smoke_test.py
python -X utf8 -m build
```

On Windows:

```bat
scripts\windows_acceptance.bat
```

## GitHub

- Confirm CI passes on Python 3.10, 3.11 and 3.12.
- Create tag `v0.1.0`.
- Create a GitHub Release from `CHANGELOG.md`.

## PyPI

Use PyPI Trusted Publishing with:

- PyPI project name: `aquote-router`
- Repository name: `aquote-router`
- Workflow file: `publish.yml`
- Environment: `pypi`
- Tag pattern: `v*`

Do not add `.pypirc` or password-based publishing files.
