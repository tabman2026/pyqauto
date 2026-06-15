# Post-release v0.2.0 Smoke Test Report

Date: 2026-06-15

## Release Targets

- GitHub Release: https://github.com/tabman2026/aquote-router/releases/tag/v0.2.0
- PyPI project: https://pypi.org/project/aquote-router/
- PyPI version verified: `0.2.0`

## Checks

| Check | Result |
|---|---|
| PyPI index lists `0.2.0` | PASS |
| Fresh venv created for verification | PASS |
| `pip install aquote-router -i https://pypi.org/simple` installs `0.2.0` | PASS |
| `import aquote_router; print(aquote_router.__version__)` | PASS |
| `from aquote_router import QuoteRouter` | PASS |
| `aquote-router --help` | PASS |
| `aquote-router minute --help` | PASS |
| `aquote-router daily --help` | PASS |
| `aquote-router kline --help` | PASS |
| `aquote-router diagnose --json` | PASS |

## Notes

Validation commands were run from outside the repository directory to avoid local
source shadowing. `diagnose --json` ran successfully and reported missing default
config files in the external working directory, which is expected for this
verification mode.
