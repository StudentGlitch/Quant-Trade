import subprocess
import os
import ast
from pathlib import Path
from loguru import logger
from src.data.duckdb_repo import DuckDBRepo
from src.qa.git_manager import GitManager
from src.api.core.push_alerts import VAPIDPushService

class RemediationAgent:
    """An LLM agent that ingests flagged inefficient functions and rewrites them using GitOps."""
    
    def __init__(self, repo: DuckDBRepo, workspace_root: str):
        self.repo = repo
        self.workspace_root = Path(workspace_root)
        self.git_manager = GitManager(workspace_root)
        self.push_service = VAPIDPushService()
        
    async def process_pending_anomalies(self):
        """Query anomalies and rewrite code using Hermes LLM and GitOps."""
        anomalies_df = self.repo.con.execute("""
            SELECT anomaly_id, file_path, anomaly_type, description 
            FROM identified_anomalies 
            WHERE status = 'PENDING_REVIEW' 
            AND anomaly_type IN ('O(N^2) LOOP', 'Vectorization Failure')
        """).df()

        for _, row in anomalies_df.iterrows():
            anomaly_id = row['anomaly_id']
            file_path = row['file_path']
            anomaly_type = row['anomaly_type']
            
            if not os.path.exists(file_path):
                continue
                
            try:
                # 1. Fetch raw source code
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()
                
                # 2. Extract specific function (simplified for MVP)
                # In a real system, we'd use AST to extract the specific function identified in the anomaly
                
                prompt = (
                    "Rewrite this function to use strictly vectorized NumPy/Pandas operations. "
                    "Preserve the exact input/output typing signatures. Do not change the underlying mathematical logic.\n\n"
                    f"```python\n{source_code}\n```\n\nRespond ONLY with the rewritten code."
                )
                
                # 3. Execute LLM Swarm Call
                result = subprocess.run(
                    ["python", "-m", "hermes_agent", "-q", prompt],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    new_code = result.stdout.strip()
                    if "```python" in new_code:
                        new_code = new_code.split("```python")[1].split("```")[0].strip()
                    elif "```" in new_code:
                        new_code = new_code.split("```")[1].strip()
                    
                    # 4. Dry-run validation (pytest)
                    # For MVP, assume a mock success. In production, we'd write to a temp file and run pytest.
                    
                    # 5. GitOps: Create branch, apply fix, commit
                    func_name = self._extract_function_name(description=row['description'])
                    branch_name = f"medic/fix-{anomaly_type.lower().replace(' ', '-')}-{func_name}"
                    
                    self.git_manager.create_branch(branch_name)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_code)
                    
                    commit_message = f"[AUTO-MEDIC] Optimized {func_name} to resolve {anomaly_type}."
                    commit_hash = self.git_manager.commit_file(file_path, commit_message)
                    
                    # 6. Update anomaly state
                    self.repo.con.execute("""
                        UPDATE identified_anomalies
                        SET git_branch_name = ?, commit_hash = ?, status = 'PENDING_REVIEW'
                        WHERE anomaly_id = ?
                    """, [branch_name, commit_hash, anomaly_id])
                    
                    logger.info(f"Remediation agent successfully generated branch {branch_name} for anomaly {anomaly_id}.")
                    
                    # 7. Restore main branch
                    self.git_manager.restore_main()
                    
                    # 8. Trigger Push Notification (Conceptual integration) -> Implemented
                    self.push_service.send_medic_alert(f"Code Medic has generated a new optimization branch for review: {branch_name}")

            except Exception as e:
                logger.error(f"Failed to process anomaly {anomaly_id}: {e}")
                self.repo.con.execute("UPDATE identified_anomalies SET status = 'FAILED_REMEDIATION' WHERE anomaly_id = ?", [anomaly_id])
                self.git_manager.restore_main() # Ensure we don't stay on a broken branch

    def _extract_function_name(self, description: str) -> str:
        """Helper to extract function name from description text."""
        # Simple extraction logic: look for text inside single quotes
        import re
        match = re.search(r"'(.*?)'", description)
        if match:
            return match.group(1)
        return "unknown_func"
