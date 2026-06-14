"""Exception types for aquote-router."""


class QuoteRouterError(Exception):
    """Base exception for all router errors."""


class ConfigurationError(QuoteRouterError):
    """Raised when local configuration is invalid or incomplete."""


class SourcePolicyError(ConfigurationError):
    """Raised when source policy is invalid."""


class AdapterError(QuoteRouterError):
    """Raised when an adapter cannot complete a source request."""


class SourceUnavailableError(AdapterError):
    """Raised when a configured source is unavailable or returns no records."""


class NoAvailableSourceError(QuoteRouterError):
    """Raised after every allowed source failed."""

