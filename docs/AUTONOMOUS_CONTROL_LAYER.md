# Autonomous Control Layer

Task028 adds L6: Autonomous Control Layer for source stability. It observes
router outcomes and keeps runtime recovery state for data infrastructure only.

## Purpose

The layer provides:

- system auto recovery
- anomaly detection
- score decay model
- self-healing mechanism

It does not select stocks, forecast returns, generate strategies, control
positions, connect to brokers, connect to QMT, or trigger trades.

## Recovery vs Governance

Governance and source policy define which sources are allowed for each feature.
L6 does not edit that policy and does not add a new real data source.

Recovery is a runtime state machine over already allowed sources:

- `NORMAL`: source is usable.
- `DEGRADED`: recent source attempt failed.
- `BLOCKED`: schema drift is observed and the source is temporarily blocked by
  self-healing state.

The router still starts from `SourcePolicy.sources_for(feature)`. L6 only ranks
currently allowed and registered candidates so normal sources are tried before
degraded or blocked sources. If a degraded source is the only available source,
it can still be observed again and recover.

## Anomaly Detection Purpose

Anomaly detection is used to explain operational instability:

- sudden full failure: all attempted sources fail in one router request
- temporary instability: failures and successes alternate inside the observation
  window
- observation window: early events are marked `OBSERVING` before an instability
  is confirmed

The detector is diagnostic. It does not create strategy signals or trading
signals.

## Decay Model Purpose

The source weight decay model uses:

```text
score = old * 0.9 + new * 0.1
```

`new` is `1.0` for a successful source attempt and `0.0` for a failed attempt.
The score is only used as a stability hint when ranking already allowed sources.
It is not a return score, alpha score, stock score, or trading score.

## Self-Healing

Self-healing tracks schema drift signals from existing quality checks. Missing
required columns and schema-drift warnings increase drift score. When a later
successful observation proves the drift has decreased to zero, L6 unblocks the
source and restores recovery state to `NORMAL`.

The mechanism does not patch third-party data, silently fill required fields, or
return data that failed validation.

## Public APIs

`MarketRouter` now exposes:

```python
router.autonomy_status()
router.recovery_state()
router.anomaly_report()
router.source_weight_decay()
```

Each API is read-only from the caller perspective and reports runtime state.

## Safety Boundaries

L6 explicitly does not provide:

- trading system behavior
- strategy or prediction output
- investment advice
- broker, QMT, account, cookie, or token integration
- automatic order execution
- stock selection or return prediction

The project remains a local market-data source router and adapter framework.

## Acceptance

Task028 acceptance commands:

```powershell
chcp 65001 | Out-Null
python -X utf8 -m pytest -q
python -X utf8 -m ruff check .
python -X utf8 scripts/check_release.py
python -X utf8 scripts/smoke_test.py
python -X utf8 -m build
```

Default tests and smoke checks remain offline. Live smoke still requires
`ENABLE_LIVE_SMOKE_TEST=1`.
