from __future__ import annotations

from pyqauto.stability import MAJOR, MINOR, PATCH, REJECTED, VersionPolicy


def test_version_policy_classifies_patch_minor_and_major_rules() -> None:
    policy = VersionPolicy()

    assert policy.classify_change({"bugfix": True}) == PATCH
    assert policy.classify_change({"new_stability_layer": True}) == MINOR
    assert policy.classify_change({"source_policy_change": True}) == MAJOR
    assert set(policy.rules()) == {PATCH, MINOR, MAJOR}


def test_version_policy_rejects_out_of_boundary_capabilities() -> None:
    policy = VersionPolicy()
    decision = policy.evaluate_change({"broker_integration": True})

    assert decision.level == REJECTED
    assert decision.allowed is False
    assert policy.is_allowed_change({"auto_trade": True}) is False
