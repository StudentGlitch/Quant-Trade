import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "swarm_state.db"
OUT_PATH = BASE_DIR / "logs" / "verifier_diagnostics_report.json"


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def main() -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_exists": DB_PATH.exists(),
        "queues": {},
        "verifier_health": {},
        "stale_items": [],
    }
    if not DB_PATH.exists():
        OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report: {OUT_PATH}")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        statuses = [
            "DISCOVERED",
            "SOLVING",
            "READY_FOR_VERIFICATION",
            "VERIFYING",
            "READY_FOR_SUBMISSION",
            "SUBMITTED_UNVERIFIED",
            "SUBMITTED",
            "FAILED",
            "BLOCKED",
        ]
        for status in statuses:
            report["queues"][status] = conn.execute(
                "SELECT COUNT(*) FROM bounties WHERE status=?",
                (status,),
            ).fetchone()[0]

        report["stale_items"] = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, status, discovered_at
                FROM bounties
                WHERE status IN ('READY_FOR_VERIFICATION', 'VERIFYING')
                  AND discovered_at <= datetime('now', '-15 minutes')
                ORDER BY discovered_at ASC
                LIMIT 50
                """
            ).fetchall()
        ]

        if _table_exists(conn, "verifier_runs"):
            rollup = conn.execute(
                """
                SELECT
                    COUNT(*) AS runs_60m,
                    COALESCE(SUM(processed_count), 0) AS processed_60m,
                    COALESCE(SUM(empty_run), 0) AS empty_60m
                FROM verifier_runs
                WHERE created_at >= datetime('now', '-60 minutes')
                """
            ).fetchone()
            latest = conn.execute(
                """
                SELECT created_at, queue_size, processed_count, failed_count, elapsed_ms
                FROM verifier_runs
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            report["verifier_health"] = {
                "runs_last_60m": rollup["runs_60m"],
                "processed_last_60m": rollup["processed_60m"],
                "empty_runs_last_60m": rollup["empty_60m"],
                "last_run": dict(latest) if latest else None,
            }
        else:
            report["verifier_health"] = {"error": "verifier_runs table missing"}

    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote report: {OUT_PATH}")


if __name__ == "__main__":
    main()
