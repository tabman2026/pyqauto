# Task 026 Governance Report

Date: 2026-06-22

## Scope

Implemented the L5 Runtime Governance Layer for pyqauto:

- `pyqauto/governance/runtime_engine.py`
- `pyqauto/governance/health_monitor.py`
- `pyqauto/governance/decision_engine.py`
- `pyqauto/governance/state_machine.py`

The layer is read-only. It observes existing router audit records and latest
live probe reports. It does not change quote, K-line, source policy, or audit
record schemas.

## System State Evolution

| Simulation | Expected state path | Reason |
|---|---|---|
| Fresh router | `NORMAL` | No runtime failures or schema drift observed. |
| pytdx failure followed by fallback success | `NORMAL -> DEGRADED` | pytdx failed and a fallback source returned data. |
| All configured sources fail | `NORMAL -> READONLY` | No data source returned records. |
| Live probe schema drift | `NORMAL -> BLOCKED` | Schema drift exceeded the decision threshold. |
| Severe state clears | `BLOCKED/READONLY/DEGRADED -> RECOVERY -> NORMAL` | State machine requires one recovery check before normal. |

## Health Score History

Scores are 0-100 and use success rate, timeout rate, schema drift rate, and
fallback rate.

| Event | pytdx | akshare | efinance | overall |
|---|---:|---:|---:|---:|
| No observations | 100.0 | 100.0 | 100.0 | 100.0 |
| pytdx timeout plus fallback | below 100.0 | 100.0 | 100.0 | below 100.0 |
| akshare schema drift | 100.0 | below 100.0 | 100.0 | below 100.0 |
| All observed sources fail | below 100.0 | unchanged unless observed | unchanged unless observed | below 100.0 |

## Decision Trace Samples

Fallback success sample:

```json
{
  "state": "DEGRADED",
  "why_this_state": "pytdx failed and a fallback source returned data",
  "failed_sources": ["pytdx:primary"],
  "fallback_chain": ["pytdx:primary"],
  "schema_validation_result": {
    "status": "not_checked",
    "schema_drift_fields": []
  }
}
```

Schema drift sample:

```json
{
  "state": "BLOCKED",
  "why_this_state": "schema drift exceeded threshold 0.0: 2.0",
  "failed_sources": [],
  "fallback_chain": [],
  "schema_validation_result": {
    "status": "schema_drift",
    "schema_drift_fields": ["akshare_em_spot:last_price"]
  }
}
```

## Failure Simulation Results

| Test file | Coverage |
|---|---|
| `tests/test_runtime_state_machine.py` | State transitions and recovery behavior. |
| `tests/test_health_score.py` | Health score decline from timeout, fallback, and schema drift. |
| `tests/test_decision_engine.py` | `BLOCKED`, `DEGRADED`, `READONLY`, and `NORMAL` decisions plus trace fields. |
| `tests/test_governance_integration.py` | Router fallback, all-source failure, live probe schema drift, and public governance APIs. |

## Audit Conclusion

Runtime governance reuses the existing audit record structure as its route-call
input. It does not add new persisted audit columns and does not alter JSONL or
SQLite audit output formats.

## Acceptance Result

Implementation is ready for the required offline validation commands:

```bash
python -X utf8 -m pytest -q
python -X utf8 -m ruff check .
python -X utf8 scripts/check_release.py
python -X utf8 scripts/smoke_test.py
python -X utf8 -m build
```

Boundary check: this task adds data quality and runtime state inspection only.
It does not add order execution, account login, or performance claims.
