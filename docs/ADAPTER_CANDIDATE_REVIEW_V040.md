# v0.4.0 Adapter Candidate Review

This document is a candidate adapter admission review for pyqauto v0.4.0
planning. It is not an implementation promise. The candidates below are not
officially supported by the current package and are not part of the default
fallback chain.

Candidate adapters are not part of the default fallback chain.

Candidate normalizers are test-only contracts, not public adapter APIs.

Related v0.4.0 gates:

- [CANDIDATE_NORMALIZE_CONTRACT_V040.md](CANDIDATE_NORMALIZE_CONTRACT_V040.md)
- [V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md](V040_ADAPTER_IMPLEMENTATION_CHECKLIST.md)

## Scope And Sources Read

Reviewed candidates:

- efinance: official docs at <https://efinance.readthedocs.io/> and official
  repository at <https://github.com/Micro-sheep/efinance>.
- baostock: official website at <https://www.baostock.com/>, official PyPI page
  and source distribution at <https://pypi.org/project/baostock/>.
- mootdx: official repository and docs folder at
  <https://github.com/mootdx/mootdx>; the README also points to historical
  readthedocs material.

No live data request was made for this review. Mock raw schema files are small
shape samples only. Candidate adapters remain manual research subjects until
live probe, unit rules, schema guard, and audit acceptance pass.

## Admission Matrix

| 候选源 | 适合用途 | 不适合用途 | 实时行情 | 分钟K线 | 日K | 指数 | 复权 | 需要登录 | 返回结构 | 单位风险 | 失败模式 | 推荐结论 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| efinance | Optional mock adapter research for Eastmoney-style realtime quotes and K-line shape checks. | Default fallback, unvalidated public records, or replacing pytdx K-line policy. | Yes, `ef.stock.get_realtime_quotes(fs=...)` covers A-share groups, ETF, LOF, and index groups by `fs`. | Yes, `ef.stock.get_quote_history(klt=1/5/15/30/60)`. | Yes, `klt=101`; weekly/monthly use `102/103`. | Realtime index groups are exposed through `fs`; K-line index coverage needs live validation. | `fqt=0/1/2` for none/forward/backward in official docs/source. | No account login in the reviewed public API path. | pandas DataFrame for one request; history returns DataFrame or dict of DataFrame for multiple symbols. | Medium: official fields expose `成交量` and `成交额`, but admission must mark unit as `unknown` until per-endpoint live probe confirms shares/lots and yuan scale. | KeyError for invalid `fs`, empty DataFrame, upstream search/cache mismatch, remote timeout, schema drift. | ready_for_mock |
| baostock | Optional historical K-line mock adapter research where session lifecycle and ResultData cursor can be tested offline. | Realtime quote source, default fallback, or public records without login/session audit. | No realtime quote API was confirmed for pyqauto scope. | Yes, source/demo confirms `frequency="5"` and minute fields; official examples also mention minute field sets. | Yes, `frequency="d"`; weekly/monthly field sets are documented in examples. | Official demos include index K-line example; field compatibility still needs live validation. | `adjustflag="3"` none and `"2"` forward are confirmed by official PyPI/source examples; other flags require documentation check before use. | Yes, `bs.login()` before query and `bs.logout()` after query. | `ResultData` cursor with `error_code`, `error_msg`, `fields`, and row data; examples build pandas DataFrame. | Medium/high: `volume`, `amount`, and `pctChg` units must remain `unknown` until validated by unit tests and live probe. | Not logged in, parameter error, start date after end date, non-zero `error_code`, network receive error, empty cursor. | ready_for_mock |
| mootdx | Reference for pytdx-family server probing and optional mock adapter shape comparison. | Independent default adapter, replacement for pyqauto policy/audit layer, or unvalidated alternative to existing pytdx adapter. | Yes, `Quotes.factory(market="std").quotes(symbol=[...])`. | Yes, `bars(frequency=0/1/2/3/7/8)` and `minute/minutes`; docs warn one minute-like endpoint may be unreliable. | Yes, `bars(frequency=4/9)` for daily-like bars. | Yes, `index(...)` is documented for index K-line. | Docs show `adjust="qfq"` and `adjust="hfq"` for `bars`, `k`, and `ohlc`; exact standard semantics must be tested. | No account login, but it requires reachable TDX-style quote servers. | pandas DataFrame or None after tdxpy/pytdx-style calls. | High: wraps TDX-family raw fields, so `vol` and `amount` units remain `unknown` until compared with current pytdx adapter. | Best server probe failure, timeout, empty DataFrame, tdxpy validation exception, connection close, config generation side effects. | needs_more_research |

## Candidate Conclusions

- `efinance`: `ready_for_mock` only. It has clear public functions and field
  names, but its units and index K-line behavior must be verified before any
  public record path exists.
- `baostock`: `ready_for_mock` for historical K-line only. The login/session and
  `ResultData` cursor should be modeled before considering live probe.
- `mootdx`: `needs_more_research` as an independent adapter. It may be more
  useful as a pytdx server / API wrapper reference than as a separate fallback.
  It must not replace pytdx in the default policy.

## Admission Gates Before Any Runtime Wiring

1. Add adapter tests and field standardization tests before implementation.
2. Keep candidates out of default `config/source_policy.example.yaml`.
3. Mark all uncertain units as `unknown` until live probe proves them.
4. Run explicit live probe only under an opt-in environment switch.
5. Reject any row that fails schema guard before it can become a public record.
6. Record audit attempts, selected source, rejection reason, and trace id.
7. Update official docs only after the adapter is actually wired and tested.

## Audit Conclusion

The review found enough official material to design mock raw schema files and
draft mapping/unit rules. It did not find enough evidence to enable any
candidate in the default fallback chain. The current policy should remain
pytdx plus easyquotation for realtime and pytdx-only for K-line APIs.
