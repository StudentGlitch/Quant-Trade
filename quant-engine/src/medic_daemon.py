import asyncio
import schedule
import time
import sys
import os
from pathlib import Path
from loguru import logger

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.data.duckdb_repo import DuckDBRepo
from src.qa.static_analyzer import StaticAnalyzer
from src.qa.remediation_agent import RemediationAgent

class MedicDaemon:
    """Continuous background healing daemon."""

    def __init__(self, db_path: str, workspace_root: str):
        self.repo = DuckDBRepo(db_path)
        self.repo.__enter__() # Ensure connection is open for daemon life
        self.workspace_root = workspace_root
        self.analyzer = StaticAnalyzer(self.repo)
        self.remediator = RemediationAgent(self.repo, workspace_root)

    def run_static_analysis(self):
        """Sweep codebase for anomalies (every 6 hours)."""
        logger.info("Running scheduled static analysis sweep...")
        try:
            self.analyzer.run_analysis(target_dir="src/")
            logger.success("Static analysis sweep complete.")
        except Exception as e:
            logger.error(f"Scheduled static analysis failed: {e}")

    async def run_remediation(self):
        """Wake up remediation agent to process anomalies (daily)."""
        logger.info("Waking up remediation agent...")
        try:
            await self.remediator.process_pending_anomalies()
            logger.success("Remediation cycle complete.")
        except Exception as e:
            logger.error(f"Scheduled remediation failed: {e}")

    def process_logs(self):
        """Read code_profiling_logs for bottlenecks (hourly)."""
        logger.info("Analyzing profiling logs for bottlenecks...")
        try:
            # Conceptually: Query code_profiling_logs and insert into identified_anomalies if threshold exceeded
            # This is partly handled inside the decorator, but this sweep handles aggregate analysis.
            pass
        except Exception as e:
            logger.error(f"Log processing failed: {e}")

    async def start_loop(self):
        """Initialize and start the background loop."""
        logger.info("Medic Daemon started.")
        
        # Schedule tasks
        schedule.every(1).hours.do(self.process_logs)
        schedule.every(6).hours.do(self.run_static_analysis)
        
        # Daily remediation (e.g., at 02:00)
        schedule.every().day.at("02:00").do(lambda: asyncio.run(self.run_remediation()))

        while True:
            schedule.run_pending()
            await asyncio.sleep(60)

if __name__ == "__main__":
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, "storage", "db", "quant_data.duckdb")
    
    daemon = MedicDaemon(db_path, BASE_DIR)
    
    # Run initial analysis sweep
    daemon.run_static_analysis()
    
    # Start loop
    asyncio.run(daemon.start_loop())
