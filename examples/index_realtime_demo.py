"""Index realtime demo.

Live sources may be unstable. Run only when you accept live network access.
"""

from aquote_router import QuoteRouter


def main() -> None:
    router = QuoteRouter.from_config(
        pytdx_servers_path="config/pytdx_servers.example.json",
        source_policy_path="config/source_policy.example.yaml",
        audit_jsonl_path="logs/aquote_router_audit.jsonl",
        audit_sqlite_path="logs/aquote_router_audit.sqlite3",
    )
    records = router.index_realtime(["000001", "399001"])
    for record in records:
        print(record.to_dict())


if __name__ == "__main__":
    main()
