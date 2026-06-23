# pyqauto V1 API Freeze

This document freezes the pyqauto v1 public router API surface for the formal
`pyqauto` namespace. `QuoteRouter` is the public name. `MarketRouter` and the
legacy `astock_source_router` namespace remain compatibility aliases to the same
implementation; they must not fork behavior.

Freeze candidate version: `1.0.0rc2`. This is a prerelease candidate only and
must not be treated as the final `1.0.0` release.

## Frozen APIs

The following `QuoteRouter` methods are the v1 frozen API:

- `router.realtime_quotes(codes: list | tuple | str | None = None) -> pandas.DataFrame`
- `router.full_realtime_quotes(codes: list | tuple | str | None = None) -> pandas.DataFrame`
- `router.index_realtime(codes: list | tuple | str | None = None) -> pandas.DataFrame`
- `router.minute_kline(code: str, *, period: str = "5", adjust: str = "") -> pandas.DataFrame`
- `router.daily_kline(code: str, *, start_date: str, end_date: str, adjust: str = "") -> pandas.DataFrame`
- `router.kline(code: str, *, start_date: str | None = None, end_date: str | None = None, period: str = "daily", adjust: str = "") -> pandas.DataFrame`
- `router.status() -> dict`
- `router.health() -> dict`
- `router.decision_trace() -> dict`
- `router.get_system_state() -> str`
- `router.source_health() -> dict`
- `router.source_scores(feature: str | None = None) -> dict`
- `router.select_best_source(context: dict | None = None) -> dict`
- `router.reliability_graph() -> dict`
- `router.autonomy_status() -> dict`
- `router.recovery_state(source: str | None = None, feature: str | None = None) -> list[dict]`
- `router.anomaly_report(source: str | None = None, feature: str | None = None) -> list[dict]`
- `router.source_weight_decay(source: str | None = None, feature: str | None = None) -> list[dict]`
- `router.meta_decision(context: dict | None = None) -> dict`
- `router.meta_state(context: dict | None = None) -> dict`
- `router.meta_explain(context: dict | None = None) -> dict`
- `router.system_brain(context: dict | None = None) -> dict`
- `router.stability_status(current_time: datetime | None = None) -> dict`
- `router.diagnose() -> dict`

Legacy methods such as `get_realtime_quotes()`, `get_daily_kline()`,
`get_minute_kline()`, `fetch_result()`, and `health_report()` remain supported,
but they are outside this v1 freeze scope.

## Return Structures

`router.meta_decision()` returns exactly these top-level keys:

- `system_state`
- `recommended_source`
- `decision_reason`
- `winning_rule`
- `conflict_resolution_path`
- `module_contributions`

`router.meta_explain()` returns exactly these top-level keys:

- `decision_trace`
- `conflict_resolution_path`
- `module_contributions`
- `decision_reason`

`router.source_health()` returns exactly these top-level keys:

- `api_version`
- `sources`
- `health`

`router.stability_status()` returns exactly these top-level keys:

- `system_uptime_score`
- `failure_rate_24h`
- `schema_drift_trend`
- `source_health_trend`

`router.diagnose()` returns exactly these top-level keys:

- `api_version`
- `router`
- `registered_sources`
- `source_policy`
- `cache_enabled`
- `sqlite_audit_enabled`
- `autonomy`
- `source_health`
- `safety_boundaries`

`router.realtime_quotes()` returns a standardized `pandas.DataFrame` for the
`realtime_quotes` feature. The required standard columns are the
`FULL_REALTIME_REQUIRED_COLUMNS` defined in `astock_source_router.core.schema`.

`router.kline()` returns a standardized `pandas.DataFrame`. Daily periods
(`daily`, `day`, `1d`, `d`) route to `daily_kline` and require `start_date` and
`end_date`. Minute periods (`1`, `5`, `15`, `30`, `60`, with optional `m`
suffix) route to `minute_kline`.

## Frozen Behavior

The v1 API freeze prohibits:

- changing the top-level return keys listed above;
- changing field meanings for the frozen API;
- changing source policy semantics;
- changing fallback ordering or fallback exhaustion behavior;
- converting meta APIs into strategy, prediction, advisory, broker, QMT, or
  auto-trading interfaces;
- turning the project into a hosted market-data API server or redistribution
  service.

## Audit Conclusion

The v1 API layer is a local data infrastructure API only. It exposes market-data
routing, health, diagnosis, and read-only meta decisions. It does not output buy
or sell advice, position sizing, return promises, or automated trading logic.
