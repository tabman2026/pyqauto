# v0.4.0 Adapter Unit Rules Draft

These rules are candidate-only. They are not current runtime behavior and do
not make efinance, baostock, or mootdx officially supported sources.

Related v0.4.0 gates:

- [CANDIDATE_NORMALIZE_CONTRACT_V040.md](CANDIDATE_NORMALIZE_CONTRACT_V040.md)
- [V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md](V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md)

pyqauto standard semantics:

- `volume_shares`: traded volume in shares.
- `amount_yuan`: traded amount in RMB yuan.
- Percent-like source fields must be represented as percent numbers when
  accepted. For example, `1.23` means `1.23%`, not `0.0123`.
- Any uncertain upstream unit is `unknown` and blocks public records until a
  unit test and live probe prove the conversion.

## Unit Rules By Candidate

| Candidate | Upstream field | Upstream unit | Standard field | Standard unit | Draft conversion | Status |
|---|---|---|---|---|---|---|
| efinance realtime | `成交量` | unknown | `volume_shares` | shares | none until verified | unknown |
| efinance realtime | `成交额` | unknown | `amount_yuan` | yuan | none until verified | unknown |
| efinance K-line | `成交量` | unknown | `volume_shares` | shares | none until verified | unknown |
| efinance K-line | `成交额` | unknown | `amount_yuan` | yuan | none until verified | unknown |
| baostock K-line | `volume` | unknown | `volume_shares` | shares | none until verified | unknown |
| baostock K-line | `amount` | unknown | `amount_yuan` | yuan | none until verified | unknown |
| mootdx quote | `vol` | unknown | `volume_shares` | shares | none until compared with current pytdx adapter | unknown |
| mootdx quote | `amount` | unknown | `amount_yuan` | yuan | none until compared with current pytdx adapter | unknown |
| mootdx K-line | `vol` | unknown | `volume_shares` | shares | none until compared with current pytdx adapter | unknown |
| mootdx K-line | `amount` | unknown | `amount_yuan` | yuan | none until compared with current pytdx adapter | unknown |

## Percent Fields

| Candidate | Field | Draft interpretation | Admission note |
|---|---|---|---|
| efinance | `涨跌幅`, `振幅`, `换手率` | percent number | Official examples display percent-like values. Keep as percent numbers only after schema tests confirm type. |
| baostock | `pctChg`, `turn` | unknown | Do not accept into public records until compared with official examples and live probe. |
| mootdx | quote/bar change fields when present | unknown | Do not infer decimal versus percent from a field name. |

## Adjustment Fields

| Candidate | Upstream field | Values confirmed by official material | Draft standard expression | Status |
|---|---|---|---|---|
| efinance | `fqt` request parameter | `0` none, `1` forward, `2` backward | raw metadata: `adjust=none/forward/backward` | ready_for_mock |
| baostock | `adjustflag` request/response field | `"3"` none, `"2"` forward | raw metadata: `adjust=none/forward`; backward needs more research | ready_for_mock |
| mootdx | `adjust` request parameter | `qfq`, `hfq` in docs | raw metadata: `adjust=forward/backward` only after comparison tests | needs_more_research |

## Guard Rule

If an adapter cannot prove conversion to `volume_shares` and `amount_yuan`, the
normalized row must be rejected before public output. `unknown` is an explicit
unit value, not a placeholder for guessing.

Candidate normalize reports must expose `unit_status` as `known`, `unknown`,
`converted`, or `rejected`. Candidate normalizers are test-only contracts, not
public adapter APIs.
