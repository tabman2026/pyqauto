from __future__ import annotations

import os


def main() -> int:
    if os.environ.get("ENABLE_LIVE_SMOKE_TEST") == "1":
        from smoke_test_live import main as smoke_main
    else:
        from smoke_test_offline import main as smoke_main

    return smoke_main()


if __name__ == "__main__":
    raise SystemExit(main())
