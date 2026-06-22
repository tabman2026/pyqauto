# v0.4.0 Candidate Normalize Contract

This document defines the mock normalize contract for v0.4.0 adapter
candidates. efinance, baostock, and mootdx remain candidates only.

candidate normalizers are test-only contracts, not public adapter APIs. They
exercise fixture shape, field mapping, unit status, and rejection behavior
before any formal adapter code is written under `pyqauto/adapters`.

## What Candidate Normalize Means

Candidate normalize is an offline contract step:

```text
mock raw -> candidate standard -> validate -> report
```

It reads stored mock raw schema fixtures, maps fields to candidate standard
records, validates required fields and units, and emits a report containing
`candidate_records`, `public_records`, `rejected_records`, `schema_drift_fields`,
and `unit_status`.

It does not make a formal adapter, does not update the default fallback chain,
does not publish v0.4.0, and does not change package runtime behavior.

## Candidate Source Names

Candidate source names must include the `_candidate` suffix:

- `efinance_candidate`
- `baostock_candidate`
- `mootdx_candidate`

The source names `efinance`, `baostock`, and `mootdx` are reserved for a future
formal adapter review. Mock contracts must not use those names as if they were
current supported sources.

## Standard Field Semantics

Candidate quote records align to these standard fields:

- `symbol`
- `name`
- `price`
- `open`
- `high`
- `low`
- `pre_close`
- `volume_shares`
- `amount_yuan`
- `datetime`
- `source`
- `source_level`
- `trace_id`
- `raw`

Candidate K-line records align to these standard fields:

- `symbol`
- `datetime`
- `open`
- `high`
- `low`
- `close`
- `volume_shares`
- `amount_yuan`
- `period`
- `source`
- `source_level`
- `trace_id`
- `raw`

Current public dataclasses expose `volume` and `amount`; in this contract those
fields carry `volume_shares` and `amount_yuan` semantics only after units are
known or converted. If units are unknown, the mock record may keep the standard
field names present with `None`, but it must not enter `public_records`.

## Report Contract

Every candidate normalize report must include:

- `contract_version`
- `candidate_normalizer`
- `candidate_source`
- `source`
- `source_api`
- `kind`
- `status`
- `unit_status`
- `standard_fields`
- `current_model_field_semantics`
- `field_mapping`
- `field_mapping_doc`
- `unit_rules_doc`
- `raw_columns`
- `schema_drift_fields`
- `missing_raw_fields`
- `row_reports`
- `candidate_records`
- `public_records`
- `rejected_records`
- `rejected_count`
- `public_count`

`public_records` may contain rows only after complete standard validation.
Rows with missing core fields, unknown volume units, unknown amount units, or
schema drift must be moved to `rejected_records`.

Each rejected record must include a non-empty `rejected_reason`.
`schema_drift_fields` must be traceable through `missing_raw_fields`, where each
entry names the standard field and the raw field candidates that were absent.

`unit_status` must be one of:

```text
known / unknown / converted / rejected
```

`unknown` is explicit. It is not a placeholder for guessing. A row with unknown
`volume_shares` or `amount_yuan` units must not enter `public_records`.

## Candidate-Specific Contracts

`efinance_candidate` covers realtime quote and K-line mock normalize from:

- `tests/fixtures/adapter_candidates/efinance_realtime_raw_sample.json`
- `tests/fixtures/adapter_candidates/efinance_kline_raw_sample.json`

`baostock_candidate` covers K-line mock normalize from:

- `tests/fixtures/adapter_candidates/baostock_kline_raw_sample.json`

`frequency` and `adjustflag` must be preserved in metadata or raw context.
Session requirements stay in documentation and are not simulated by default
tests.

`mootdx_candidate` covers quote and K-line mock normalize from:

- `tests/fixtures/adapter_candidates/mootdx_quote_raw_sample.json`
- `tests/fixtures/adapter_candidates/mootdx_kline_raw_sample.json`

mootdx may be a pytdx server / API wrapper reference. It must not replace pytdx
or become a default fallback without a separate adapter and source policy
review.

## Upgrade Gate

A candidate can be considered for formal adapter implementation only after:

1. Official docs and source behavior are reviewed.
2. Mock raw schema fixtures are fixed.
3. Field mapping and unit rules are confirmed.
4. Mock normalize tests pass.
5. Missing-field and schema drift rejection tests pass.
6. Live probe passes under explicit opt-in.
7. Audit records include source attempts, selected source, trace id, and
   rejection reasons.
8. Source policy, DATA_SOURCES, RETURN_FIELDS, CLI docs, and release docs are
   updated.
9. The adapter remains outside the default fallback chain unless a separate
   policy change explicitly approves it.

## Audit Conclusion

The v0.4.0 candidate normalize contract establishes test-only behavior for
mock schemas. It does not enable candidate sources, does not expose unverified
records, and does not change the current conservative default source policy.
