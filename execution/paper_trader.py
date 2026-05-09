
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.utils.math_utils import QuantJSONEncoder

logger = logging.getLogger("execution")

def execute_signals(signals: list):
    """Log signals to a paper-trading ledger."""
    log_file = Path(__file__).resolve().parent.parent / "logs" / "paper_trade_log.jsonl"
    log_file.parent.mkdir(exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    
    with open(log_file, "a", encoding="utf-8") as f:
        for signal in signals:
            signal['timestamp'] = timestamp
            # PRD Bug Fix: Use QuantJSONEncoder
            f.write(json.dumps(signal, cls=QuantJSONEncoder) + "\n")
            logger.info(f"SIGNAL: {signal['ticker']} | Type: {signal['signal_type']} | Conf: {signal['model_confidence']:.2f}")

if __name__ == "__main__":
    # Example
    mock_signals = [
        {"ticker": "AAPL", "signal_type": 1, "model_confidence": 0.85, "suggested_position_size": 0.05}
    ]
    execute_signals(mock_signals)
