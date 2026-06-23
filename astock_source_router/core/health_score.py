from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class HealthStat:
    source: str
    feature: str
    success_count: int = 0
    failure_count: int = 0
    empty_count: int = 0
    field_missing_count: int = 0
    stale_count: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    recent_successes: list[bool] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return self.success_count + self.failure_count

    def success_rate(self) -> float:
        total = self.total_count
        return self.success_count / total if total else 1.0

    def p95_latency(self) -> float:
        if not self.latencies_ms:
            return 0.0
        if len(self.latencies_ms) < 2:
            return self.latencies_ms[-1]
        return statistics.quantiles(self.latencies_ms, n=20)[-1]

    def avg_latency(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.fmean(self.latencies_ms)

    def empty_rate(self) -> float:
        total = max(1, self.total_count)
        return self.empty_count / total

    def field_complete_rate(self) -> float:
        total = max(1, self.total_count)
        return max(0.0, 1 - self.field_missing_count / total)

    def freshness_rate(self) -> float:
        total = max(1, self.total_count)
        return max(0.0, 1 - self.stale_count / total)

    def recent_failure_count(self) -> int:
        return sum(1 for ok in self.recent_successes[-10:] if not ok)

    def score(self, timeout_ms: float = 8000.0) -> float:
        success_score = self.success_rate() * 30
        p95 = self.p95_latency()
        avg = self.avg_latency()
        p95_score = max(0.0, 1 - min(p95, timeout_ms) / timeout_ms) * 10 if p95 else 10
        avg_score = max(0.0, 1 - min(avg, timeout_ms) / timeout_ms) * 10 if avg else 10
        field_complete_score = self.field_complete_rate() * 15
        non_empty_score = max(0.0, 1 - self.empty_rate()) * 10
        freshness_score = self.freshness_rate() * 10
        recent_score = max(0.0, 1 - self.recent_failure_count() / 10) * 15
        return round(
            success_score
            + p95_score
            + avg_score
            + field_complete_score
            + non_empty_score
            + freshness_score
            + recent_score,
            3,
        )


class HealthScoreBoard:
    def __init__(self, persist_path: Path | None = None) -> None:
        self.persist_path = persist_path
        self._stats: dict[tuple[str, str], HealthStat] = {}
        if persist_path is not None:
            self.load()

    def _get(self, source: str, feature: str) -> HealthStat:
        key = (source, feature)
        if key not in self._stats:
            self._stats[key] = HealthStat(source=source, feature=feature)
        return self._stats[key]

    def record_success(self, source: str, feature: str, latency_ms: float) -> None:
        stat = self._get(source, feature)
        stat.success_count += 1
        stat.latencies_ms.append(float(latency_ms))
        stat.latencies_ms = stat.latencies_ms[-200:]
        stat.recent_successes.append(True)
        stat.recent_successes = stat.recent_successes[-50:]
        self.save()

    def record_failure(
        self,
        source: str,
        feature: str,
        *,
        empty: bool = False,
        field_missing: bool = False,
        stale: bool = False,
        latency_ms: float | None = None,
    ) -> None:
        stat = self._get(source, feature)
        stat.failure_count += 1
        if empty:
            stat.empty_count += 1
        if field_missing:
            stat.field_missing_count += 1
        if stale:
            stat.stale_count += 1
        if latency_ms is not None:
            stat.latencies_ms.append(float(latency_ms))
            stat.latencies_ms = stat.latencies_ms[-200:]
        stat.recent_successes.append(False)
        stat.recent_successes = stat.recent_successes[-50:]
        self.save()

    def score(self, source: str, feature: str, timeout_ms: float = 8000.0) -> float:
        return self._get(source, feature).score(timeout_ms=timeout_ms)

    def report(self, timeout_ms: float = 8000.0) -> list[dict[str, object]]:
        rows = []
        for stat in self._stats.values():
            row = asdict(stat)
            row["score"] = stat.score(timeout_ms=timeout_ms)
            row["success_rate"] = round(stat.success_rate(), 4)
            row["avg_latency_ms"] = round(stat.avg_latency(), 3)
            row["p95_latency_ms"] = round(stat.p95_latency(), 3)
            row["empty_rate"] = round(stat.empty_rate(), 4)
            row["field_complete_rate"] = round(stat.field_complete_rate(), 4)
            row["freshness_rate"] = round(stat.freshness_rate(), 4)
            row["recent_failure_count"] = stat.recent_failure_count()
            rows.append(row)
        rows.sort(key=lambda x: (str(x["feature"]), -float(x["score"])))
        return rows

    def save(self) -> None:
        if self.persist_path is None:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(stat) for stat in self._stats.values()]
        self.persist_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        if self.persist_path is None or not self.persist_path.exists():
            return
        payload = json.loads(self.persist_path.read_text(encoding="utf-8"))
        for row in payload:
            row.pop("score", None)
            row.pop("success_rate", None)
            row.pop("avg_latency_ms", None)
            row.pop("p95_latency_ms", None)
            row.pop("empty_rate", None)
            row.pop("field_complete_rate", None)
            row.pop("freshness_rate", None)
            row.pop("recent_failure_count", None)
            stat = HealthStat(**row)
            self._stats[(stat.source, stat.feature)] = stat
