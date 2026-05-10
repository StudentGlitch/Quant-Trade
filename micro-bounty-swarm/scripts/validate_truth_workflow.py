import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "db" / "swarm_state.db"
OUT_PATH = BASE_DIR / "logs" / "truth_validation_report.json"


def main() -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_exists": DB_PATH.exists(),
        "checks": {},
    }

    if not DB_PATH.exists():
        report["checks"]["fatal"] = "Database missing"
        OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report: {OUT_PATH}")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) FROM bounties").fetchone()[0]
        submitted = conn.execute("SELECT COUNT(*) FROM bounties WHERE status='SUBMITTED'").fetchone()[0]
        submitted_unverified = conn.execute(
            "SELECT COUNT(*) FROM bounties WHERE status='SUBMITTED_UNVERIFIED'"
        ).fetchone()[0]
        solved_l3 = conn.execute(
            "SELECT COUNT(*) FROM bounties WHERE status='SUBMITTED' AND proof_link IS NOT NULL"
        ).fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM bounties WHERE status='FAILED'").fetchone()[0]

        has_verification_logs = (
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='verification_logs'"
            ).fetchone()[0]
            > 0
        )
        verification_logs = 0
        if has_verification_logs:
            verification_logs = conn.execute("SELECT COUNT(*) FROM verification_logs").fetchone()[0]

    submitted_attempts = submitted + submitted_unverified
    report["checks"] = {
        "total_bounties": total,
        "submitted": submitted,
        "submitted_unverified": submitted_unverified,
        "submitted_attempts": submitted_attempts,
        "solved_l3": solved_l3,
        "failed": failed,
        "verification_logs_present": has_verification_logs,
        "verification_logs_count": verification_logs,
        "acceptance_rate_l3": round((solved_l3 / submitted_attempts), 3) if submitted_attempts else 0.0,
    }

    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote report: {OUT_PATH}")


if __name__ == "__main__":
    main()
