import sqlite3
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "swarm_state.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
DB_PATH.parent.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    filename=LOG_DIR / "system_execution.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("db_manager")

def init_db():
    """Initialize the SQLite database with the schema."""
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        _migrate_bounties_table(conn)
        _create_aux_tables(conn)
        conn.commit()
    logger.info("Database initialized successfully.")


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _migrate_bounties_table(conn: sqlite3.Connection) -> None:
    """Apply additive schema migrations for older DB files."""
    add_columns = [
        ("verification_score", "REAL DEFAULT 0.0"),
        ("verification_notes", "TEXT"),
        ("verification_hard_fail", "INTEGER DEFAULT 0"),
        ("verification_reason", "TEXT"),
        ("confidence_level", "TEXT DEFAULT 'LOW'"),
        ("proof_link", "TEXT"),
        ("proof_verified_at", "TIMESTAMP"),
        ("resolution_level", "TEXT DEFAULT 'L1'"),
    ]
    for column_name, column_type in add_columns:
        if not _column_exists(conn, "bounties", column_name):
            conn.execute(f"ALTER TABLE bounties ADD COLUMN {column_name} {column_type}")


def _create_aux_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bounty_id TEXT NOT NULL,
            score REAL DEFAULT 0.0,
            confidence_level TEXT DEFAULT 'LOW',
            hard_fail INTEGER DEFAULT 0,
            passed INTEGER DEFAULT 0,
            reasons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(bounty_id) REFERENCES bounties(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iteration INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            lessons_learned TEXT,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verifier_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_size INTEGER DEFAULT 0,
            processed_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            empty_run INTEGER DEFAULT 0,
            elapsed_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

def add_bounty(bounty_id: str, platform: str, url: str, description: str, reward_estimate: float = 0.0):
    """Add a new discovered bounty using the Incremental Save pattern."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO bounties (id, platform, url, description, reward_estimate, status)
                VALUES (?, ?, ?, ?, ?, 'DISCOVERED')
                ON CONFLICT(id) DO NOTHING
                """,
                (bounty_id, platform, url, description, reward_estimate)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error adding bounty {bounty_id}: {e}")

def update_status(bounty_id: str, status: str):
    """Update the status of a specific bounty."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            if status in ('SUBMITTED', 'SUBMITTED_UNVERIFIED'):
                conn.execute(
                    "UPDATE bounties SET status = ?, submitted_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, bounty_id)
                )
            else:
                conn.execute("UPDATE bounties SET status = ? WHERE id = ?", (status, bounty_id))
            conn.commit()
        logger.info(f"Updated bounty {bounty_id} to {status}")
    except Exception as e:
        logger.error(f"Error updating status for {bounty_id}: {e}")

def get_bounties_by_status(status: str) -> list[dict]:
    """Retrieve bounties by their current status."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM bounties WHERE status = ?", (status,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error retrieving bounties with status {status}: {e}")
        return []

def log_revenue(bounty_id: str, platform: str, url: str, estimated_reward: float):
    """Incrementally save successful submissions to the revenue tracker CSV."""
    csv_path = LOG_DIR / "revenue_tracker.csv"
    write_header = not csv_path.exists()
    
    try:
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["timestamp", "bounty_id", "platform", "url", "estimated_reward"])
            writer.writerow([datetime.now().isoformat(), bounty_id, platform, url, estimated_reward])
        logger.info(f"Logged potential revenue for {bounty_id}: ${estimated_reward}")
    except Exception as e:
        logger.error(f"Failed to log revenue for {bounty_id}: {e}")


def save_verification_result(
    bounty_id: str,
    score: float,
    notes: str,
    confidence_level: str,
    hard_fail: bool,
    reason: str,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE bounties
            SET verification_score = ?,
                verification_notes = ?,
                confidence_level = ?,
                verification_hard_fail = ?,
                verification_reason = ?,
                resolution_level = CASE WHEN ? THEN 'L2' ELSE resolution_level END
            WHERE id = ?
            """,
            (score, notes, confidence_level, int(hard_fail), reason, int(not hard_fail), bounty_id),
        )
        conn.execute(
            """
            INSERT INTO verification_logs (bounty_id, score, confidence_level, hard_fail, passed, reasons)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (bounty_id, score, confidence_level, int(hard_fail), int(not hard_fail), reason),
        )
        conn.commit()


def record_verifier_run(
    queue_size: int,
    processed_count: int,
    failed_count: int,
    elapsed_ms: int,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO verifier_runs (queue_size, processed_count, failed_count, empty_run, elapsed_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                queue_size,
                processed_count,
                failed_count,
                int(processed_count == 0),
                elapsed_ms,
            ),
        )
        conn.commit()


def save_proof_link(bounty_id: str, proof_link: Optional[str]) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        if proof_link:
            conn.execute(
                """
                UPDATE bounties
                SET proof_link = ?,
                    proof_verified_at = CURRENT_TIMESTAMP,
                    resolution_level = 'L3',
                    status = 'SUBMITTED'
                WHERE id = ?
                """,
                (proof_link, bounty_id),
            )
        else:
            conn.execute(
                "UPDATE bounties SET status = 'SUBMITTED_UNVERIFIED' WHERE id = ?",
                (bounty_id,),
            )
        conn.commit()

if __name__ == "__main__":
    init_db()
