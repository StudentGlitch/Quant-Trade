import subprocess
import json
import ast
import uuid
from loguru import logger
from typing import Optional
from src.data.duckdb_repo import DuckDBRepo

class StaticAnalyzer:
    """Orchestrates static analysis using ruff, bandit, and custom AST parsing."""

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def run_analysis(self, target_dir: str = "src/"):
        logger.info(f"Running static analysis on {target_dir}")
        self._run_ruff(target_dir)
        self._run_bandit(target_dir)

    def _run_ruff(self, target_dir: str):
        try:
            result = subprocess.run(
                ["ruff", "check", target_dir, "--output-format=json"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                findings = json.loads(result.stdout)
                for finding in findings:
                    self._log_anomaly(
                        file_path=finding.get("filename", ""),
                        line_number=finding.get("location", {}).get("row", 0),
                        anomaly_type="LINT_ERROR",
                        severity="MEDIUM",
                        description=finding.get("message", "")
                    )
        except Exception as e:
            logger.error(f"Ruff execution failed: {e}")

    def _run_bandit(self, target_dir: str):
        try:
            result = subprocess.run(
                ["bandit", "-r", target_dir, "-f", "json"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                data = json.loads(result.stdout)
                for issue in data.get("results", []):
                    self._log_anomaly(
                        file_path=issue.get("filename", ""),
                        line_number=issue.get("line_number", 0),
                        anomaly_type="SECURITY_FLAW",
                        severity=issue.get("issue_severity", "LOW"),
                        description=issue.get("issue_text", "")
                    )
        except Exception as e:
            logger.error(f"Bandit execution failed: {e}")

    def analyze_vectorization(self, file_path: str, function_name: str):
        """Parse AST to detect non-vectorized operations like iterrows."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    for child in ast.walk(node):
                        if isinstance(child, ast.Attribute) and child.attr in ["iterrows", "apply"]:
                            self._log_anomaly(
                                file_path=file_path,
                                line_number=getattr(child, "lineno", 0),
                                anomaly_type="Vectorization Failure",
                                severity="CRITICAL",
                                description=f"Function '{function_name}' uses non-vectorized pandas method '{child.attr}'"
                            )
        except Exception as e:
            logger.error(f"AST parsing failed for {file_path}: {e}")

    def _log_anomaly(self, file_path: str, line_number: int, anomaly_type: str, severity: str, description: str):
        anomaly_id = str(uuid.uuid4())
        self.repo.con.execute("""
            INSERT OR REPLACE INTO identified_anomalies 
            (anomaly_id, file_path, line_number, anomaly_type, severity, description, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW')
        """, [anomaly_id, file_path, line_number, anomaly_type, severity, description])
