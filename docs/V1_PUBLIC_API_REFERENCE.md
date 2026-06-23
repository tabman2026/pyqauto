# pyqauto V1 Public API Reference

Task 032 freezes the v1 release-candidate public API around the formal
`pyqauto` namespace.

## Namespace Contract

- Formal public namespace: `pyqauto`
- Public router class: `pyqauto.QuoteRouter`
- Compatibility alias: `pyqauto.MarketRouter`
- Legacy compatibility namespace: `astock_source_router`

`QuoteRouter`, `MarketRouter`, and `astock_source_router.MarketRouter` point to
the same implementation. The legacy namespace is packaged only to avoid breaking
existing local users during the v1 transition. It is not a second public core and
must not be maintained independently.

## Frozen Router API Snapshot

The frozen public Router API count is 23.

| API | Signature | Return |
| --- | --- | --- |
| `realtime_quotes` | `(codes=None)` | `pandas.DataFrame` |
| `full_realtime_quotes` | `(codes=None)` | `pandas.DataFrame` |
| `index_realtime` | `(codes=None)` | `pandas.DataFrame` |
| `minute_kline` | `(code, *, period="5", adjust="")` | `pandas.DataFrame` |
| `daily_kline` | `(code, *, start_date, end_date, adjust="")` | `pandas.DataFrame` |
| `kline` | `(code, *, start_date=None, end_date=None, period="daily", adjust="")` | `pandas.DataFrame` |
| `status` | `()` | `dict` |
| `health` | `()` | `dict` |
| `decision_trace` | `()` | `dict` |
| `get_system_state` | `()` | `str` |
| `source_health` | `()` | `dict` |
| `source_scores` | `(feature=None)` | `dict` |
| `select_best_source` | `(context=None)` | `dict` |
| `reliability_graph` | `()` | `dict` |
| `autonomy_status` | `()` | `dict` |
| `recovery_state` | `(source=None, feature=None)` | `list[dict]` |
| `anomaly_report` | `(source=None, feature=None)` | `list[dict]` |
| `source_weight_decay` | `(source=None, feature=None)` | `list[dict]` |
| `meta_decision` | `(context=None)` | `dict` |
| `meta_state` | `(context=None)` | `dict` |
| `meta_explain` | `(context=None)` | `dict` |
| `system_brain` | `(context=None)` | `dict` |
| `stability_status` | `(*, current_time=None)` | `dict` |

The exact Python signature strings are frozen in
`tests/test_v1_public_api_snapshot.py`.

## Required Return Keys

`status()` returns:

- `api_version`
- `system_state`
- `state`
- `registered_sources`
- `active_recovery`
- `latest_decision_trace`
- `safety_boundaries`

`health()` returns:

- `api_version`
- `system_state`
- `source_health`
- `autonomy`

`source_health()` returns:

- `api_version`
- `sources`
- `health`

`source_scores()` returns:

- `api_version`
- `feature`
- `overall_reliability_score`
- `ranked_sources`

`select_best_source()` returns:

- `api_version`
- `feature`
- `system_state`
- `recommended_source`
- `best_source`
- `selection_status`
- `ranked_sources`
- `reason`

`reliability_graph()` returns:

- `api_version`
- `system_state`
- `features`
- `source_health`

`meta_decision()` returns:

- `system_state`
- `recommended_source`
- `decision_reason`
- `winning_rule`
- `conflict_resolution_path`
- `module_contributions`

`meta_state()` returns:

- `governance`
- `graph`
- `autonomy`
- `merged`

`meta_explain()` returns:

- `decision_trace`
- `conflict_resolution_path`
- `module_contributions`
- `decision_reason`

`system_brain()` returns:

- `role`
- `system_state`
- `recommended_source`
- `decision_reason`
- `meta_state`
- `meta_decision`
- `meta_explain`
- `safety_boundaries`

`stability_status()` returns:

- `system_uptime_score`
- `failure_rate_24h`
- `schema_drift_trend`
- `source_health_trend`

## Error Behavior

- Data APIs raise existing router exceptions such as `AllSourcesFailedError` or
  `DataQualityError` when all configured sources fail or validation rejects the
  record.
- Selection APIs return `recommended_source=None` when the local system state is
  `READONLY` or `BLOCKED`.
- Stability APIs never mutate router source policy, fallback ordering, health
  scores, recovery state, or public records.

## Audit Conclusion

The v1 public API is a local market-data routing and observability API. It has no
trading, strategy, prediction, account, broker, QMT, order, position, or
investment-advice interface.

## Acceptance Result

The API snapshot is enforced by `tests/test_v1_public_api_snapshot.py`.
