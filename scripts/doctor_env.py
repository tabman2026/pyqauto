from __future__ import annotations

import importlib
import json
import locale
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _module_status(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return {
            "importable": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "importable": True,
        "version": getattr(module, "__version__", None),
        "file": getattr(module, "__file__", None),
    }


def _build_report() -> dict[str, Any]:
    module_checks = {
        "pytest": _module_status("pytest"),
        "ruff": _module_status("ruff"),
        "pandas": _module_status("pandas"),
        "astock_source_router": _module_status("astock_source_router"),
    }
    in_virtualenv = sys.prefix != sys.base_prefix
    critical_checks = {
        "in_virtualenv": in_virtualenv,
        "pytest_importable": bool(module_checks["pytest"]["importable"]),
        "pandas_importable": bool(module_checks["pandas"]["importable"]),
        "package_importable": bool(module_checks["astock_source_router"]["importable"]),
    }

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
            },
            "prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "in_virtualenv": in_virtualenv,
        },
        "modules": module_checks,
        "cwd": str(Path.cwd()),
        "operating_system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "utf8": {
            "utf8_mode": sys.flags.utf8_mode,
            "filesystem_encoding": sys.getfilesystemencoding(),
            "preferred_encoding": locale.getpreferredencoding(False),
            "PYTHONUTF8": os.environ.get("PYTHONUTF8"),
        },
        "critical_checks": critical_checks,
        "overall_status": "PASS" if all(critical_checks.values()) else "FAIL",
        "notes": {
            "ruff": "optional_quality_check; missing ruff is recorded but does not fail doctor_env",
        },
    }


def main() -> int:
    report = _build_report()
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / "environment_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
