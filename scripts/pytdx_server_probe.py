"""Compatibility wrapper for the packaged pytdx probe."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aquote_router.pytdx_probe import (  # noqa: E402,F401
    DEFAULT_CONFIG,
    DEFAULT_COUNT,
    DEFAULT_LOCAL_CONFIG,
    DEFAULT_MINUTE_PERIOD,
    DEFAULT_OUTPUT,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    ROLE_SEQUENCE,
    ServerCandidate,
    _build_active_config,
    _candidate_from_hq_host,
    _candidate_from_stock_ip,
    _candidate_from_values,
    _dedupe_candidates,
    _display_path,
    _error_text,
    _fastest_available_server,
    _load_config_candidates,
    _load_official_pytdx_servers,
    _probe_candidate,
    _probe_candidates,
    _result_sort_key,
    build_arg_parser,
    main,
    run_probe,
)

if __name__ == "__main__":
    raise SystemExit(main())
