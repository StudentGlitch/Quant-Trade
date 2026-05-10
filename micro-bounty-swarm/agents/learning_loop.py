
import sys
import logging
import sqlite3
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db_manager import DB_PATH

logger = logging.getLogger("learning_loop")

def summarize_iteration(iteration: int):
    """Summarize iteration outcomes and persist deterministic learning hints."""
    logger.info(f"Running learning loop for iteration {iteration}")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT status, COUNT(*) as cnt FROM bounties GROUP BY status")
            stats = {row['status']: row['cnt'] for row in cursor.fetchall()}
            
            success_count = stats.get('SUBMITTED', 0)
            failure_count = stats.get('FAILED', 0) + stats.get('BLOCKED', 0) + stats.get('SUBMITTED_UNVERIFIED', 0)
            
            if failure_count > success_count:
                lessons = "Reduce low-quality submissions and prioritize high-confidence artifacts."
            elif stats.get("SUBMITTED_UNVERIFIED", 0) > 0:
                lessons = "Increase proof-link discovery to convert unverified submissions to solved."
            else:
                lessons = "Maintain current strategy and prioritize repositories with repeated success."
             
            # Persist learning
            conn.execute(
                "INSERT INTO agent_learning (iteration, agent_name, lessons_learned, success_count, failure_count) VALUES (?, ?, ?, ?, ?)",
                (iteration, "orchestrator", lessons, success_count, failure_count)
            )
            conn.commit()
            logger.info(f"Learning persisted: {lessons}")
            
    except Exception as e:
        logger.error(f"Error in learning loop: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        summarize_iteration(int(sys.argv[1]))
