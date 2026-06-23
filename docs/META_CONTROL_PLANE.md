# Meta Control Plane

Task029 adds `pyqauto.meta`, the single read-only decision entry for system
state, data-source selection signals, autonomy recovery signals, and conflict
arbitration.

## System Role

The Meta Control Plane does not replace Governance, the Reliability Graph, or
Autonomy. It reads their public snapshots and produces one merged view:

- `meta_state()` returns governance state, graph score, autonomy state, and the
  merged state used by the final decision.
- `meta_decision()` returns `system_state`, `recommended_source`, and
  `decision_reason`.
- `meta_explain()` returns the decision trace, conflict resolution path, and
  module contributions.
- `system_brain()` returns the global state view for operators and tests.

## Conflict Resolution Rules

The priority order is fixed:

1. `BLOCKED`
2. `READONLY`
3. `AUTONOMY_RECOVERY`
4. `GRAPH_SCORE`
5. `GOVERNANCE_NORMAL`

`BLOCKED` disables source selection. `READONLY` also disables runtime source
selection. Autonomy recovery can mark the system as `RECOVERY` while preserving
the graph source only as an allowed data-source candidate. The Reliability Graph
selects the highest ranked source only when no higher-priority conflict exists.
Governance normal is the final default when no blocking or recovery signal is
active.

## Relationship Between Subsystems

Governance owns system safety state such as `NORMAL`, `READONLY`, and
`BLOCKED`. The Reliability Graph owns source reliability scores and ranking.
Autonomy owns source recovery, anomaly, decay, and self-healing status.

The Meta Control Plane only arbitrates across these outputs. It does not mutate
governance rules, graph scoring internals, autonomy recovery internals, source
policy, field standards, or audit log structure.

## Why This Is Not a Trading System

The Meta Control Plane never places orders, connects to brokers, controls QMT,
creates strategies, predicts prices, recommends securities, or provides
position advice. Its `recommended_source` is only a market-data source candidate,
not an investment recommendation.

Safety boundaries remain false for:

- trading system
- strategy or prediction
- investment advice
- broker or QMT control
- auto trade

## Audit Conclusion

Task029 adds a read-only orchestration layer. It does not add a real data source,
does not modify source policy, does not change field standards, does not change
JSON/JSONL/SQLite audit structure, and does not introduce trading behavior.
