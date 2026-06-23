from __future__ import annotations

import pytest

from astock_source_router.autonomy.decay_model import ScoreDecayModel
from pyqauto.autonomy.decay_model import ScoreDecayModel as PyqautoScoreDecayModel


def test_decay_formula_uses_fixed_90_10_weights():
    assert ScoreDecayModel.decay(1.0, 0.0) == pytest.approx(0.9)
    assert ScoreDecayModel.decay(0.8, 0.4) == pytest.approx(0.76)
    assert PyqautoScoreDecayModel.decay(1.0, 0.0) == pytest.approx(0.9)


def test_decay_model_records_source_feature_weights():
    model = ScoreDecayModel()

    first = model.record("fake", "realtime_quotes", 0.0)
    second = model.record("fake", "realtime_quotes", 1.0)
    report = model.report(source="fake", feature="realtime_quotes")

    assert first.score == pytest.approx(0.9)
    assert second.score == pytest.approx(0.91)
    assert report == [
        {
            "source": "fake",
            "feature": "realtime_quotes",
            "score": pytest.approx(0.91),
            "observations": 2,
            "last_new_score": 1.0,
            "trend": "up",
        }
    ]
