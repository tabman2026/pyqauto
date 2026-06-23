# System Behavior Freeze

This document freezes pyqauto v1 runtime behavior. Future changes may fix bugs
inside the frozen boundaries, but they must not expand the architecture or
change the contracts below without a new major-version decision.

## Governance

The v1 governance state set is fixed:

- `NORMAL`
- `DEGRADED`
- `READONLY`
- `BLOCKED`

No additional governance states may be introduced in v1. `READONLY` and
`BLOCKED` disable runtime source selection in meta decisions. `DEGRADED` is a
recovery or stability signal, not a trading or strategy signal.

## Reliability Graph

The score model is frozen to the existing health score formula:

- success rate: 30
- p95 latency: 10
- average latency: 10
- field completeness: 15
- non-empty response: 10
- freshness: 10
- recent stability: 15

The graph may rank allowed data sources and report health. It must not become a
strategy engine, portfolio engine, trading signal engine, or hosted data
redistribution service.

## Autonomy

The v1 autonomy layer is limited to:

- recovery
- anomaly detection
- score decay
- self-healing for schema drift recovery

It must not add strategy, prediction, investment advice, broker, QMT, order
routing, account, or auto-trading capability.

## Meta

The v1 meta layer is limited to:

- read-only decision aggregation;
- explainability for that decision.

The meta layer may select or explain a data-source candidate. It must not
recommend trades, positions, expected returns, timing, or automated actions.

## Audit Conclusion

V1 system behavior is frozen as financial data infrastructure. The system can
recover and explain routing decisions, but it cannot cross into investment
advice, trading strategy, broker control, or automatic trading.
