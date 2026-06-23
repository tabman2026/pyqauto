# Version Governance Policy

Task031 defines PATCH, MINOR, and MAJOR version-governance rules for pyqauto.

## PATCH

Use PATCH for compatible maintenance changes:

- bug fixes with no public API change
- documentation updates
- tests and release-check updates
- internal refactors that preserve behavior
- stability threshold tuning that does not change existing public contracts

PATCH changes must not alter source policy, standard fields, audit log schema,
Governance state, Graph behavior, Autonomy behavior, or Meta behavior.

## MINOR

Use MINOR for new compatible capabilities:

- new optional modules
- new read-only public APIs that do not change existing APIs
- new stability or health reporting surfaces
- new optional adapters after adapter contract tests and field normalization
  tests are added

MINOR changes can add capability but must preserve existing Router return keys,
source policy behavior, field standards, and audit log structure.

## MAJOR

Use MAJOR for breaking or freeze-sensitive changes:

- breaking public API changes
- Router return-key changes
- source policy changes
- field standard or unit changes
- JSON, JSONL, or SQLite audit structure changes
- Governance state changes
- Graph, Autonomy, or Meta behavior changes
- migrations required by existing users

MAJOR changes require explicit migration notes and updated freeze documents.

## Rejected Scope

Some changes are not versionable project changes and must be rejected instead:

- trading-system behavior
- strategy or prediction output
- investment advice
- stock selection
- return prediction
- broker integration
- QMT integration
- account, credential, session, or login-state integration
- automatic order execution

## System Freeze Rules

When a change touches any frozen contract, the release must update the relevant
documentation and tests before acceptance:

- `README.md`
- `SOURCE_POLICY.md`
- `PROJECT_STATE.md`
- `docs/V1_API_FREEZE.md`
- `docs/ADAPTER_CONTRACT_V1.md`
- `docs/SYSTEM_BEHAVIOR_FREEZE.md`
- release and smoke checks

Default tests remain offline. Real-source smoke tests must still be explicitly
enabled with `ENABLE_LIVE_SMOKE_TEST=1`.

## Not a Trading System

Version governance is release governance only. It does not create strategies,
signals, stock recommendations, position advice, broker controls, QMT controls,
or automatic trading.
