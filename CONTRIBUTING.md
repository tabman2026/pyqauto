# Contributing

Thank you for helping improve aquote-router.

## Development

```bash
python -X utf8 -m pip install -e ".[dev,test]"
python -X utf8 -m pytest -q
python -X utf8 scripts/check_release.py
```

## Rules

- Keep Python source files UTF-8.
- Use explicit `encoding="utf-8"` for text reads and writes.
- Default tests must not connect to live quote sources.
- Live smoke tests must require `ENABLE_LIVE_SMOKE_TEST=1`.
- Add adapter tests before adding a real data source.
- Preserve normalized fields and audit schema compatibility.
- Do not commit private configuration, credentials or local absolute paths.

## Pull Requests

Every pull request should include:

- What changed.
- Which tests ran.
- Whether source policy or audit schema changed.
- Any user-visible compatibility notes.
