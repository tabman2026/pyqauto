from __future__ import annotations


class SourceRouterError(Exception):
    """Base exception for source router errors."""


class UnsupportedFeatureError(SourceRouterError):
    """Raised when a source adapter does not support a requested feature."""


class SourceNotRegisteredError(SourceRouterError):
    """Raised when policy references a source that is not registered."""


class SourceUnavailableError(SourceRouterError):
    """Raised when an optional third-party dependency is not installed or unavailable."""


class PytdxAllServersFailed(SourceUnavailableError):
    """Raised when every runtime pytdx server candidate fails."""

    def __init__(
        self,
        function_name: str,
        attempts: list[dict[str, object]],
        warnings: list[str] | None = None,
    ) -> None:
        self.function_name = function_name
        self.attempts = attempts
        self.warnings = warnings or []
        summary = ", ".join(
            f"{attempt.get('endpoint') or attempt.get('ip')}:{attempt.get('error_type')}"
            for attempt in attempts[:5]
        )
        super().__init__(
            f"all pytdx servers failed for {function_name}; "
            f"attempt_count={len(attempts)}; first_attempts={summary}"
        )


class DataQualityError(SourceRouterError):
    """Raised when a source returns invalid, empty, stale, or incomplete data."""


class AllSourcesFailedError(SourceRouterError):
    """Raised when all candidate sources fail for a feature."""

    def __init__(self, feature: str, trace: list[dict[str, object]]) -> None:
        self.feature = feature
        self.trace = trace
        super().__init__(f"All sources failed for feature={feature}. trace={trace}")
