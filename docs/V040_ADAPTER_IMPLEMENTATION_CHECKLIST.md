# v0.4.0 Adapter Implementation Checklist

Use this checklist only when a candidate moves from mock normalize contract to
formal adapter implementation. Candidate normalize work alone is not a release
gate and is not runtime wiring.

## Required Gates

1. Official documentation has been read.
2. Mock raw schema has been fixed.
3. Field mapping has been confirmed.
4. Unit rules have been confirmed.
5. Normalize mock tests pass.
6. Missing-field rejection tests pass.
7. Schema drift guard passes.
8. Live probe passes under explicit opt-in.
9. Audit records pass with source attempts, selected source, trace id, record
   count, and rejection reason.
10. Source policy draft passes review.
11. DATA_SOURCES has been updated.
12. RETURN_FIELDS has been updated.
13. CLI documentation has been updated.
14. Not in the default fallback chain unless explicitly approved.
15. Release checks pass before publishing: pytest / ruff / check_release / smoke_test / build.

## Boundaries

- Do not add candidate adapters to default fallback from mock normalize work.
- Do not tag or publish from candidate normalize work.
- Do not create public adapter files until the implementation task is approved.
- Do not accept rows whose units are unknown.
- Do not allow records rejected by schema guard into public output.
- Keep candidate source names suffixed with `_candidate` until formal support is
  approved.

## Acceptance Result

This checklist is a pre-implementation gate for v0.4.0 planning. It does not
change the current supported adapter list or current package version.
