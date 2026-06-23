# Stability Layer

Task031 adds L8: `pyqauto.stability`, the production stability layer for
long-running pyqauto deployments.

## Purpose

The layer observes local runtime history and source-health snapshots. It helps
operators answer four stability questions:

- Is the system uptime score still acceptable?
- Did the 24 hour failure rate rise?
- Is schema drift increasing?
- Are key source health trends improving, stable, degrading, or unknown?

The public status entry is:

```python
from pyqauto.stability import stability_status

status = stability_status(events=audit_rows, health_rows=health_rows)
```

It returns:

```text
system_uptime_score
failure_rate_24h
schema_drift_trend
source_health_trend
```

`QuoteRouter.stability_status(current_time=None)` is the formal Router entry for
the same observational report. `current_time` may be supplied in tests; naive
datetimes are treated as UTC.

## Metric Semantics

- `system_uptime_score`: `100 * (1 - failure_rate_24h)`, rounded to three
  decimals.
- `failure_rate_24h`: failed events divided by all events inside the rolling
  24 hour UTC window. Events without a parseable timestamp are excluded from the
  24 hour calculation. Future events are excluded.
- `schema_drift_trend`: trend from `DriftDetector`, using observations sorted by
  timestamp when timestamps are present.
- `source_health_trend`: per-source trend from `HealthTracker`, using health
  rows sorted by timestamp when timestamps are present.

Sample thresholds:

- Schema/fallback/latency drift requires at least four observations by default.
- Source health trend requires at least two scores per source.
- When the minimum is not met, trend values are `insufficient_data`.

Latency spike thresholds are configurable through `DriftDetector` and the module
level `stability_status()` helper. Defaults:

- `latency_spike_factor = 2.0`
- `latency_min_delta_ms = 500.0`

## Drift Detection Meaning

Drift detection compares the older half of local observations with the recent
half. It reports:

- `schema_drift_increase`: missing required fields or explicit schema drift
  markers are becoming more frequent.
- `fallback_frequency_increase`: more requests need multiple sources or an
  explicit fallback marker.
- `latency_spike_detected`: recent p95 latency is materially higher than the
  baseline window.

These are operational signals only. They do not change source policy, do not
silently repair data, and do not allow invalid public records to pass quality
checks.

## Health Tracking

Health tracking summarizes the trend for:

- `pytdx`
- `akshare`
- `efinance`

The trend values are `improving`, `stable`, `degrading`, or
`insufficient_data`. Health status is based on the latest local score:

- `healthy`: score is at least 80
- `degraded`: score is at least 50 and below 80
- `unhealthy`: score is below 50
- `unknown`: no local score is available

## Restart Semantics

The Stability Layer itself is stateless. It recomputes reports from supplied
events and health rows.

Persisted inputs:

- Router audit JSONL and SQLite logs are persisted under `RouterConfig.log_dir`.
- Source health scores are persisted in `source_health.json` under
  `RouterConfig.log_dir`.

Non-persisted runtime state:

- Autonomy recovery windows, anomaly in-memory counters, circuit breaker state,
  and rate limiter state are not restored after process restart.
- Stability reports do not persist their own derived trend state.

## System Linkage

The production control responsibilities remain separate:

- Governance controls system state.
- Graph controls data-source ranking and selection.
- Autonomy controls recovery.
- Meta controls read-only decision arbitration.
- Stability controls long-term operational stability reporting.

L8 reads observations. It does not mutate Governance, Graph, Autonomy, Meta,
source policy, field standards, or audit log schema.

## System Freeze Rules

The following remain frozen unless a dedicated version-governance change is
approved:

- V1 Router API return keys
- default source policy
- standard field names and units
- JSON, JSONL, and SQLite audit structures
- Governance state set
- Graph scoring semantics
- Autonomy recovery behavior
- Meta conflict-resolution behavior

Stability findings can recommend human review or system freeze in release
documents, but the L8 code does not enforce trading controls or runtime
execution controls.

## Not a Trading System

The Stability Layer is not a trading system. It does not place orders, connect
to brokers, connect to QMT, manage accounts, produce strategies, predict
returns, select stocks, recommend positions, or provide investment advice.

## Audit Conclusion

Task031 adds an isolated read-only stability layer. It does not add a real data
source, does not modify source policy, does not change field standards, does not
change audit log structure, and does not introduce trading behavior.
