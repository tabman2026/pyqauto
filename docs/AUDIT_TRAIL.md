# Audit Trail

aquote-router can write each routed call to JSONL and SQLite.

## Top-level Fields

- `trace_id`: Unique id for one router call.
- `api_name`: Public API name, such as `realtime_quotes`.
- `symbols`: Requested symbols.
- `started_at`: UTC timestamp when the call started.
- `finished_at`: UTC timestamp when the call finished.
- `duration_ms`: Total duration in milliseconds.
- `selected_source`: Source that returned records.
- `selected_source_level`: Source level, such as `primary`, `hot_backup` or `backup`.
- `attempts`: Per-source attempt objects.
- `fallback_chain`: Failed sources before the selected source.
- `success`: Whether the call returned records.
- `error_type`: Final error type when the call failed.
- `error_message`: Final error message when the call failed.
- `record_count`: Number of normalized records returned.

## SQLite Tables

`quote_router_audit` stores one row per router call.

`quote_router_attempts` stores one row per source attempt and links back through `trace_id`.

The SQLite writer uses standard `sqlite3` and does not require an ORM.
