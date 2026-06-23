# V1 Architecture

pyqauto v1 is a local financial data infrastructure system. Its stable
production architecture has five layers.

## 1. Public API

The frozen public API is documented in `docs/V1_API_FREEZE.md`:

- `router.meta_decision()`
- `router.meta_explain()`
- `router.source_health()`
- `router.kline()`
- `router.realtime_quotes()`
- `router.diagnose()`

These APIs are local library calls. The project is not an API server and is not
a market-data redistribution service.

## 2. Source Policy and Router

`SourcePolicy` owns allowed source ordering per feature. `MarketRouter` applies
the policy, skips open circuit breakers, executes adapters, validates data
quality, records audit events, and falls back until a valid source succeeds or
all sources fail.

V1 freezes source policy semantics and fallback behavior.

## 3. Adapter Contract

Adapters implement the V1 contract documented in
`docs/ADAPTER_CONTRACT_V1.md`:

- raw fetch;
- raw schema inspection;
- normalization to standard schema and units;
- standard output validation.

Only records that pass validation are public records.

## 4. Health, Graph, and Autonomy

The health score board records success, failure, latency, emptiness, field
completeness, freshness, and recent stability. The reliability graph uses these
health signals for source ranking only.

The autonomy layer is limited to recovery, anomaly detection, score decay, and
self-healing for schema drift. It cannot become a strategy or trading system.

## 5. Meta Control Plane

The meta control plane reads governance, graph, and autonomy signals and returns
a read-only decision plus an explanation. It is the system brain for source
routing health, not a trading brain.

## Frozen Safety Boundary

V1 explicitly forbids:

- buy/sell advice;
- position sizing;
- return promises;
- strategy or prediction logic;
- broker, QMT, account, cookie, token, or login-state control;
- automatic trading;
- hosted quote API serving or data redistribution.

## Audit Conclusion

pyqauto v1 is frozen as a stable local market-data routing infrastructure. Its
interfaces support data retrieval, validation, health, diagnosis, recovery, and
explainable source selection only.
