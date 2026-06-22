# Beginner Developer Guide

This guide explains how a new contributor can design a pyqauto data source
adapter without guessing from upstream output.

## Core Ideas

pyqauto is a Python package that routes A-share quote and K-line reads through
source adapters, normalizes records, validates schema, and writes audit data.
It does not create market data. It calls public upstream Python APIs and records
which source produced each accepted record.

A data source is an upstream library or public endpoint family such as pytdx,
AKShare, efinance, easyquotation, baostock, or mootdx.

An adapter is pyqauto code that knows how to call one source, inspect the raw
payload, normalize it, and reject unsafe rows before public output.

Raw data is the upstream return value before pyqauto changes field names or
units. It may be a DataFrame, dict, list, or custom object.

A standard record is the pyqauto internal row after normalization. It contains
stable fields such as `symbol`, `price`, `open`, `high`, `low`, `pre_close`,
`volume_shares`, `amount_yuan`, `datetime`, `period`, `source`,
`source_level`, `trace_id`, and optional `raw`.

Normalize means convert upstream field names, symbols, timestamps, periods, and
units into pyqauto standard fields.

Schema drift means the upstream shape changed: a field was renamed, removed,
emptied, moved into a composite field, or changed type.

Source policy decides which adapters are eligible for each API and whether
fallback is allowed.

Fallback means trying a lower-priority source after a higher-priority source
fails or returns invalid data. K-line fallback is strict because period,
adjustment, volume, and amount semantics must match.

Audit means recording each attempted source, result, duration, selected source,
failure reason, and `trace_id`.

`trace_id` is the request identifier used to connect returned records with
audit entries.

## v0.4.0 Adapter Candidate Review Entry

The v0.4.0 candidate review documents are research entry points, not current
support statements:

- [ADAPTER_CANDIDATE_REVIEW_V040.md](ADAPTER_CANDIDATE_REVIEW_V040.md)
- [ADAPTER_FIELD_MAPPING_DRAFT_V040.md](ADAPTER_FIELD_MAPPING_DRAFT_V040.md)
- [ADAPTER_UNIT_RULES_DRAFT_V040.md](ADAPTER_UNIT_RULES_DRAFT_V040.md)
- [SOURCE_POLICY_DRAFT_V040.md](SOURCE_POLICY_DRAFT_V040.md)
- [CANDIDATE_NORMALIZE_CONTRACT_V040.md](CANDIDATE_NORMALIZE_CONTRACT_V040.md)
- [V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md](V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md)

They describe candidate adapter admission work for efinance, baostock, and
mootdx. They do not mean the current version supports these data sources, and
they do not add candidates to the default fallback chain.
Candidate normalizers are test-only contracts, not public adapter APIs.

## Why Raw Output Is Not Public Output

Never return upstream raw data directly to users. Upstream libraries do not use
the same field names, units, symbol formats, periods, adjustment rules, or error
contracts. Returning raw payloads would make pyqauto output unstable and could
silently mix incompatible rows.

Units must be unified. pyqauto standard volume is `volume_shares`; standard
amount is `amount_yuan`. If an upstream volume is lots, multiply by 100. If an
upstream amount is ten-thousand-yuan, multiply by 10000. If an upstream amount
is already yuan, keep it as yuan.

K-line fallback cannot be casual. A bar from another source is only compatible
when symbol, period, timestamp, adjustment, volume, amount, and missing-field
behavior match pyqauto rules and pass validation.

## Adapter Development Flow

1. Read official documentation and the official repository or package source.
2. Record interface purpose, parameters, return type, fields, units, and known
   errors.
3. Run a minimal raw example outside default tests.
4. Save raw schema shape only; do not save private auth material or machine
   paths.
5. Create a field mapping table.
6. Create unit rules.
7. Write the adapter class.
8. Implement `normalize_to_standard`.
9. Add schema drift guard validation.
10. Add source policy entries if the source becomes eligible.
11. Write mock tests.
12. Write an explicit live probe guarded by an environment opt-in.
13. Update `docs/DATA_SOURCES.md` and related docs.
14. Run `pytest`, `ruff`, `check_release`, `smoke_test`, `build`, and
   `git diff --check`.
15. Decide whether a version release is needed.

## How To Add An Adapter

1. Place code under `pyqauto/adapters/`.
2. Name the file after the source and endpoint family, for example
   `example_source_adapter.py`.
3. Use a class name ending in `Adapter`.
4. Implement the same public methods used by existing adapters:
   `fetch_raw`, `inspect_raw_schema`, `normalize_to_standard`, and
   `validate_standard_output`.
5. Add tests before wiring the adapter into source policy.

## Method Responsibilities

`fetch_raw` calls the upstream public API and returns the untouched payload. It
should convert upstream exceptions into pyqauto adapter errors and include
enough context for audit.

`inspect_raw_schema` records type, columns or keys, row count, sample fields,
field mapping, and unit rules. It should not record unnecessary local details.

`normalize_to_standard` converts raw rows into dictionaries with standard
fields. Do not fill missing numeric core fields with zero just to pass tests.

`validate_standard_output` calls the schema guard. Invalid rows must be marked
as rejected and must not become public records.

## Unit Rules

Every adapter must declare `unit_rules` beside its field mapping. Each rule
should name the upstream field, upstream unit, standard field, standard unit,
conversion, and a test case.

Minimum rules:

| Standard field | Standard unit | Required behavior |
|---|---|---|
| `volume_shares` | shares | Convert lots to shares when needed. |
| `amount_yuan` | yuan | Convert ten-thousand-yuan to yuan when needed; keep yuan as yuan. |
| percent fields | percent number | Keep `1.23` as `1.23%` unless a standard field says otherwise. |

## Source Policy

Add a source policy entry only after mock tests pass. For realtime APIs, policy
can allow fallback when the adapter can return the same standard quote fields.
For K-line APIs, policy must be conservative and should stay pytdx-only unless a
new source passes period, adjustment, field, and unit compatibility tests.

## Tests

Mock tests must cover:

- raw payload with expected fields;
- raw payload missing one core field;
- volume unit conversion;
- amount unit conversion;
- symbol normalization;
- period normalization for K-line adapters;
- validation rejection path;
- audit fields and `trace_id`.

Live probes must be opt-in and must not run in the default test suite. Use an
environment gate such as `ENABLE_LIVE_SMOKE_TEST=1`.

## Documentation

Update documentation when adding or changing an adapter:

- `docs/DATA_SOURCES.md` for supported role and fallback behavior.
- `docs/UNITS.md` and `docs/UNIT_RULES_FOR_ADAPTERS.md` for unit rules.
- `docs/SOURCE_POLICY.md` for source order and eligibility.
- `docs/RETURN_FIELDS.md` for public field changes.
- `docs/AUDIT_TRAIL.md` for audit shape changes.

Do not describe planned work as already supported.

## Release Decision

Do not release a package version for docs-only local work unless the PyPI page
must show the change. Release rules are in `docs/WHEN_TO_RELEASE.md`.
