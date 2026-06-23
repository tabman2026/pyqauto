# pyqauto 1.0.0rc1

`pyqauto==1.0.0rc1` is a prerelease candidate. It is not the final `1.0.0`
release.

## Highlights

- V1 public API freeze candidate for `pyqauto`.
- Adapter Contract V1 for raw schema inspection, normalization, and standard
  output validation.
- Runtime Governance for local source state and health decisions.
- Reliability Graph for source scoring, graph state, and source selection.
- Autonomous Control Layer for local recovery, anomaly identification, score
  decay, and schema drift recovery.
- Meta Control Plane for read-only cross-layer state, decisions, explanations,
  and system brain output.
- Stability Layer for uptime, failure-rate, schema-drift, and source-health
  trends.
- Cross-layer integration validation and clean wheel installation validation.

## Known Limits

- Free public data sources may be delayed, disconnected, rate-limited, timed
  out, or affected by field drift.
- The pytdx server pool may require local refresh before live use.
- Stability persistence and restart semantics follow the Task032 documentation.
- The dual namespace relationship exists only as the audited compatibility
  relationship between `pyqauto` and `astock_source_router`; independent forks of
  core behavior are not allowed.

## Safety Boundary

This project provides market-data infrastructure only. It does not provide
investment advice, trading execution, strategy signals, stock picking, broker
integration, QMT integration, account access, return promises, or automated
trading logic.

## Testing

The release candidate scope includes pytest, ruff, release checks, offline smoke
tests, package build, twine package validation, cross-layer integration, and
clean wheel installation validation.
