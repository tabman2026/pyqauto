"""Production stability layer for long-running pyqauto deployments.

The layer is observational. It reports runtime stability, drift, health trends,
and version-governance rules without mutating router behavior or source policy.
"""

from pyqauto.stability.drift_detector import DriftDetector, detect_drift
from pyqauto.stability.health_tracker import HealthTracker, source_health_trend
from pyqauto.stability.monitor import StabilityMonitor, stability_status
from pyqauto.stability.stability_engine import StabilityEngine
from pyqauto.stability.version_policy import (
    MAJOR,
    MINOR,
    PATCH,
    REJECTED,
    VersionDecision,
    VersionPolicy,
)

__all__ = [
    "MAJOR",
    "MINOR",
    "PATCH",
    "REJECTED",
    "DriftDetector",
    "HealthTracker",
    "StabilityEngine",
    "StabilityMonitor",
    "VersionDecision",
    "VersionPolicy",
    "detect_drift",
    "source_health_trend",
    "stability_status",
]
