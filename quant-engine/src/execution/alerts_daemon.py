import requests
from loguru import logger
import yaml
from pathlib import Path
from ..data.duckdb_repo import DuckDBRepo

class AlertsDaemon:
    """
    Phase 3.3: Automated Alerts Daemon.
    Watches the database for extreme outlier shifts and pushes payloads to webhooks.
    """
    
    def __init__(self, repo: DuckDBRepo, config_path: str = None):
        self.repo = repo
        base_dir = Path(__file__).resolve().parent.parent.parent
        if config_path is None:
            config_path = str(base_dir / "config" / "settings.yaml")
            
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.webhook_url = self.config.get('alerts', {}).get('webhook_url', '')

    def check_anomalies(self):
        """Query DuckDB for anomalies and trigger alerts."""
        logger.info("Alerts Daemon checking for cross-sectional anomalies...")
        
        query = """
            SELECT 
                pt.ticker, 
                m.sector,
                pt.final_blended_signal, 
                pt.cross_sectional_z_score, 
                pt.vibe,
                pt.target_weight_pct
            FROM paper_trades pt
            LEFT JOIN idx_metadata m ON pt.ticker = m.ticker
            LEFT JOIN portfolio_targets tgt ON pt.ticker = tgt.ticker AND pt.signal_date = tgt.date
            WHERE 
                pt.cross_sectional_z_score > 2.5 
                AND pt.signal_date >= CURRENT_DATE - INTERVAL 1 DAY
            ORDER BY pt.cross_sectional_z_score DESC
        """
        
        try:
            df = self.repo.execute(query).df()
            
            if df.empty:
                logger.info("No anomalies detected in the last 24 hours.")
                return
                
            for _, row in df.iterrows():
                self._send_alert(row)
                
        except Exception as e:
            logger.error(f"Alerts Daemon query failed: {e}")

    def _send_alert(self, row):
        """Format and push the Markdown payload."""
        if not self.webhook_url:
            # Fail silently if webhook URL is empty as per PRD
            logger.debug(f"Webhook URL not configured. Skipping alert for {row['ticker']}.")
            return
            
        weight_pct = row.get('target_weight_pct', 0.0) * 100
        if pd.isna(weight_pct):
            weight_pct = 0.0
            
        signal_str = "Strong Buy" if row['final_blended_signal'] > 0.65 else ("Buy" if row['final_blended_signal'] > 0.2 else "Neutral/Hold")
            
        payload = f"""
🚨 **SWARM ALPHA ALERT** 🚨
**Ticker:** {row['ticker']} ({row.get('sector', 'UNKNOWN')})
**Signal:** {signal_str} ({row['final_blended_signal']:.2f}) | **Z-Score:** {row['cross_sectional_z_score']:.2f}
**LLM Vibe:** {row.get('vibe', 'Unknown')}
**Action:** Added to Target Portfolio at {weight_pct:.1f}% weight.
"""
        logger.info(f"Triggering Webhook Alert for {row['ticker']}...")
        
        try:
            # Assuming Discord compatible webhook format for now
            data = {"content": payload}
            response = requests.post(self.webhook_url, json=data, timeout=10)
            if response.status_code not in (200, 204):
                logger.error(f"Failed to push alert. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook push failed: {e}")
