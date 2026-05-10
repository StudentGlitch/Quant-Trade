import pandas as pd
from loguru import logger
import subprocess
import os
from pathlib import Path
import json
from ..data.duckdb_repo import DuckDBRepo

class ShareholderReportGenerator:
    """
    Phase 6.3: Shareholder Letter Generation.
    Synthesizes performance, risk, and evolution into a human-friendly Markdown letter.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.report_dir = Path(__file__).resolve().parent.parent.parent / "reports" / "weekly"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._init_ledger()

    def _init_ledger(self):
        """Initialize shareholder_reports table."""
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS shareholder_reports (
                report_id VARCHAR PRIMARY KEY,
                publish_date DATE,
                markdown_content TEXT,
                prev_week_pnl DOUBLE,
                active_cio_thesis VARCHAR
            );
        """)

    def generate_weekly_letter(self):
        """Assemble context and prompt LLM to write the letter."""
        logger.info("Shareholder Report: Assembling context for weekly letter...")
        
        try:
            # 1. Gather Context
            # Week's PnL
            pnl_df = self.repo.execute("SELECT * FROM daily_pnl_ledger ORDER BY date DESC LIMIT 5").df()
            pnl_sum = pnl_df['total_equity'].iloc[0] - pnl_df['total_equity'].iloc[-1] if not pnl_df.empty else 0.0
            
            # Active features
            active_feats = self.repo.execute("SELECT feature_id, formula_code FROM feature_evolution_ledger WHERE status = 'ACTIVE'").df()
            
            # Risk regime
            risk_row = self.repo.execute("SELECT * FROM risk_metrics_ledger ORDER BY date DESC LIMIT 1").df()
            
            # Build context JSON
            context = {
                "performance": {
                    "last_week_total_equity": float(pnl_df['total_equity'].iloc[0]) if not pnl_df.empty else 0.0,
                    "weekly_pnl_idr": float(pnl_sum),
                    "benchmark_status": "Outperforming" if pnl_sum > 0 else "Underperforming" # Simplification
                },
                "intelligence": {
                    "active_features_count": len(active_feats),
                    "latest_feature": active_feats['feature_id'].iloc[-1] if not active_feats.empty else "None"
                },
                "risk": risk_row.to_dict(orient='records')[0] if not risk_row.empty else {}
            }
            
            # 2. LLM Prompt
            prompt = f"""
            ACT as the Chief Investment Officer (CIO) of a sophisticated Indonesian Quantitative Hedge Fund.
            Write a professional, 3-paragraph Weekly Shareholder Letter based on this data:
            
            {json.dumps(context, indent=2)}
            
            STRUCTURE:
            - Paragraph 1: Performance Attribution (How did we do this week against the IHSG?).
            - Paragraph 2: Darwinian Intelligence (Comment on our evolving quantitative models and feature discovery).
            - Paragraph 3: Risk Outlook (Current volatility regime and portfolio safety).
            
            FORMAT: Pure Markdown. Use bolding and lists where appropriate. 
            TONE: Institutional, transparent, and authoritative.
            """
            
            logger.info("Shareholder Report: Prompting Hermes for narrative synthesis...")
            process = subprocess.run(["python", "-m", "hermes_agent", "-z", "-q", prompt], 
                                    capture_output=True, text=True, encoding='utf-8')
            
            markdown_content = process.stdout.strip()
            
            if not markdown_content:
                markdown_content = "### Weekly Intelligence Brief\n\nAutomated report generation pending more market data."
                
            report_id = f"WEEK_{pd.Timestamp.now().strftime('%U_%Y')}"
            
            # 3. Save to DB and File
            self.repo.execute("""
                INSERT OR REPLACE INTO shareholder_reports (report_id, publish_date, markdown_content, prev_week_pnl, active_cio_thesis)
                VALUES (?, CURRENT_DATE, ?, ?, ?)
            """, [report_id, markdown_content, pnl_sum, context['risk'].get('volatility_regime', 'NORMAL')])
            
            report_path = self.report_dir / f"{report_id}.md"
            with open(report_path, "w") as f:
                f.write(markdown_content)
                
            logger.success(f"Shareholder Letter generated: {report_id}")
            return report_id
            
        except Exception as e:
            logger.error(f"Failed to generate shareholder report: {e}")
            return None
