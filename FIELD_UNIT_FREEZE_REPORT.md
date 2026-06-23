# FIELD_UNIT_FREEZE_REPORT

- generated_at: `2026-06-12T13:23:37.756785+00:00`
- overall_status: `PASS`
- mode: `offline_fixture`
- volume standard unit: `share`
- amount standard unit: `yuan`
- pct_chg standard scope: `percent`, where `1.23` means `1.23%`
- source policy changed: `no`
- lite_realtime used as full: `no`

## Results

| check | status | summary |
|---|---:|---|
| `source_policy_freeze` | `PASS` | Current source policy order matches task016 freeze. |
| `field_and_source_unit_policy` | `PASS` | Field and source unit policies are loadable and cover required sources. |
| `unit_normalizer_conversion_rules` | `PASS` | Core conversion and unknown-unit rules were checked with offline samples. |
| `dataframe_unit_metadata` | `PASS` | DataFrame normalizers preserve raw values, warnings, source fields, and unit metadata. |
| `lite_full_boundary_units` | `PASS` | lite_realtime_quotes remains isolated from full realtime units. |

## Gate

- task016 field unit freeze: `complete` when overall status is PASS or WARN without BLOCK.
- continue 5-day stability watch: `yes` when no BLOCK exists.
- allow S0 production: `no`.
- trading advice/signals/position/return output: `no`.
