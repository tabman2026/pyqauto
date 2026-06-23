# Adapter Contract V1

All pyqauto v1 adapters inherit from `BaseMarketDataAdapter` and must implement
or honor this four-step contract:

1. `fetch_raw(feature: str, **kwargs) -> pandas.DataFrame`
2. `inspect_raw_schema(raw: Any | None = None, *, feature: str | None = None, **kwargs) -> dict`
3. `normalize_to_standard(feature: str, raw: Any, *, source: str | None = None, latency_ms: float = 0.0, trace_id: str | None = None) -> pandas.DataFrame`
4. `validate_standard_output(feature: str, records: Any, *, context: dict | None = None) -> dict`

`fetch()` remains a compatibility alias for `fetch_raw()` and must not bypass the
source policy or router fallback chain.

## Required Semantics

- `fetch_raw()` calls only public source APIs through optional adapter
  dependencies. It must not embed cookies, tokens, accounts, broker sessions, or
  private login state.
- `inspect_raw_schema()` returns source, feature, row count, column names, and
  dtypes so schema drift can be audited before public output.
- `normalize_to_standard()` converts records into the project standard schema,
  normalizes units to the field unit policy, stamps `source`, and preserves
  `trace_id` when supplied.
- `validate_standard_output()` runs standard quality checks and returns
  `public_records` and `rejected_records`. Rejected records must never enter
  `public_records`.

## Unit Freeze

V1 standard units are fixed by `config/field_unit_policy.json`,
`config/source_unit_policy.json`, and `astock_source_router.core.unit_policy`:

- price fields: yuan
- `volume`: share
- `amount`: yuan
- `pct_chg`: percent

Adapters may keep raw unit metadata columns, but public numeric fields must be
standardized before they pass validation.

## Schema Drift

Schema drift is detected by comparing adapter output with
`astock_source_router.core.schema.REQUIRED_COLUMNS`. Missing required columns
are blocking drift for public output. Extra raw or metadata columns may be
retained for auditability, but they do not satisfy missing required fields.

## Trace and Source

Every validated standard output must identify its `source`. When a `trace_id` is
available, it must be carried through normalized records and audit output.

## Audit Conclusion

The V1 adapter contract standardizes local data ingestion only. It does not
authorize data redistribution, strategy decisions, broker control, or automated
trading behavior.
