# Release Status

Current stable recommendation: `pyqauto==0.3.1`.

Current release candidate: `pyqauto==1.0.0rc1`.

`1.0.0rc1` is a prerelease candidate for V1 API freeze validation. It is not the
final `1.0.0` release and is not the default recommendation for all users.

Release gates for any later final `1.0.0` task:

- `1.0.0rc1` cold-start installation passes.
- `0.3.1` to `1.0.0rc1` upgrade passes.
- `1.0.0rc1` to `0.3.1` rollback passes.
- Offline cross-layer scenarios pass.
- Multiple stability or soak validations complete.
- No blocking RC issue remains.
- Public API snapshot has no unexpected change.
- The user explicitly approves final `1.0.0`.

Audit conclusion: this project provides local market-data infrastructure only.
It does not provide investment advice, trading execution, strategy signals,
stock picking, broker integration, QMT integration, account access, return
promises, or automated trading logic.
