import json
import numpy as np
import pandas as pd
import datetime

class QuantJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to safely serialize pandas and numpy data types.
    Strict Anti-Goal Compliance: Prevents TypeError with pandas.Timestamp during LLM prompt generation.
    """
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj): # Handle NaN/NaT
            return None
        return super(QuantJSONEncoder, self).default(obj)
