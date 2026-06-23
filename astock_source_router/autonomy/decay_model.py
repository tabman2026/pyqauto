from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class DecayScore:
    source: str
    feature: str
    score: float = 1.0
    observations: int = 0
    last_new_score: float = 1.0
    trend: str = "stable"


class ScoreDecayModel:
    """Exponential source score decay.

    Formula: score = old * 0.9 + new * 0.1.
    """

    def __init__(
        self,
        *,
        old_weight: float = 0.9,
        new_weight: float = 0.1,
        initial_score: float = 1.0,
    ) -> None:
        if old_weight < 0 or new_weight < 0:
            raise ValueError("decay weights must be non-negative")
        if round(old_weight + new_weight, 10) != 1.0:
            raise ValueError("decay weights must sum to 1.0")
        self.old_weight = float(old_weight)
        self.new_weight = float(new_weight)
        self.initial_score = self._clamp(initial_score)
        self._scores: dict[tuple[str, str], DecayScore] = {}

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def decay(
        old_score: float,
        new_score: float,
        *,
        old_weight: float = 0.9,
        new_weight: float = 0.1,
    ) -> float:
        return float(old_score) * old_weight + float(new_score) * new_weight

    def record(self, source: str, feature: str, new_score: float) -> DecayScore:
        key = (source, feature)
        current = self._scores.get(key)
        old_score = current.score if current is not None else self.initial_score
        bounded_new_score = self._clamp(new_score)
        decayed = self._clamp(
            self.decay(
                old_score,
                bounded_new_score,
                old_weight=self.old_weight,
                new_weight=self.new_weight,
            )
        )
        if decayed > old_score:
            trend = "up"
        elif decayed < old_score:
            trend = "down"
        else:
            trend = "stable"
        score = DecayScore(
            source=source,
            feature=feature,
            score=round(decayed, 6),
            observations=(current.observations + 1 if current is not None else 1),
            last_new_score=bounded_new_score,
            trend=trend,
        )
        self._scores[key] = score
        return score

    def weight(self, source: str, feature: str) -> float:
        score = self._scores.get((source, feature))
        return score.score if score is not None else self.initial_score

    def report(
        self,
        *,
        source: str | None = None,
        feature: str | None = None,
    ) -> list[dict[str, object]]:
        rows = []
        for score in self._scores.values():
            if source is not None and score.source != source:
                continue
            if feature is not None and score.feature != feature:
                continue
            rows.append(asdict(score))
        rows.sort(key=lambda row: (str(row["feature"]), -float(row["score"]), str(row["source"])))
        return rows
