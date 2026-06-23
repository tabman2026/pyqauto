"""Autonomous control layer for source stability only.

The layer observes router outcomes and adjusts recovery state. It does not
produce trading signals, predictions, portfolio actions, or broker actions.
"""

from astock_source_router.autonomy.anomaly_detector import AnomalyDetector, AnomalyEvent
from astock_source_router.autonomy.decay_model import DecayScore, ScoreDecayModel
from astock_source_router.autonomy.recovery_engine import (
    AutonomousControlLayer,
    RecoveryEngine,
    RecoverySnapshot,
)
from astock_source_router.autonomy.self_healing import HealingSnapshot, SelfHealingMonitor

__all__ = [
    "AnomalyDetector",
    "AnomalyEvent",
    "AutonomousControlLayer",
    "DecayScore",
    "HealingSnapshot",
    "RecoveryEngine",
    "RecoverySnapshot",
    "ScoreDecayModel",
    "SelfHealingMonitor",
]
