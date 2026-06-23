# pyqauto Soak Test

`scripts/soak_test.py` is a local, non-CI soak test for the v1 release
candidate.

## Safety

- Default adapter: `FakeAdapter`
- Network access: no
- Trading, strategy, prediction, account, broker, QMT, order, or auto-trading:
  no
- Persistent run logs: no

The script uses a temporary directory for cache and JSONL audit files. SQLite
audit is disabled to avoid Windows temporary-file locks during cleanup. The
temporary directory is deleted after the run. The printed summary is desensitized
and contains no local absolute paths.

## Usage

Quick local check:

```powershell
chcp 65001
python -X utf8 scripts/soak_test.py --iterations 100
```

Default 30 minute run:

```powershell
chcp 65001
python -X utf8 scripts/soak_test.py
```

Memory threshold override:

```powershell
chcp 65001
python -X utf8 scripts/soak_test.py --duration-seconds 1800 --max-memory-growth-mb 32
```

## Checks

The script validates:

- memory growth stays below the configured threshold;
- system state remains one of `NORMAL`, `DEGRADED`, `READONLY`, or `BLOCKED`;
- audit record count matches loop count;
- request IDs are present and unique;
- reliability graph numeric values are finite;
- stability numeric values are finite;
- every fake-adapter call returns at least one public record.

## Audit Conclusion

The soak test is an offline durability check for Router, Reliability Graph,
Autonomy, Meta, and Stability APIs. It does not add a source, change fallback
policy, or introduce trading behavior.

## Acceptance Result

The run passes only when the JSON summary reports `"status": "PASS"`.
