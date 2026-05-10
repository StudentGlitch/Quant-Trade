import time
import tracemalloc
import uuid
from functools import wraps
from datetime import datetime
from loguru import logger

try:
    from pyinstrument import Profiler
except ImportError:
    Profiler = None

def profile_performance():
    """
    Generic decorator utilizing pyinstrument and tracemalloc
    to record time and RAM usage. Assumes applied to class methods where self.repo exists.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not Profiler:
                # logger.warning("pyinstrument not installed. Falling back to basic timing.")
                profiler = None
            else:
                profiler = Profiler()
                profiler.start()

            tracemalloc.start()
            
            start_time = time.time()
            result = func(self, *args, **kwargs)
            end_time = time.time()
            
            if profiler:
                profiler.stop()
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            exec_time_ms = (end_time - start_time) * 1000
            peak_mb = peak / (1024 * 1024)
            
            execution_id = str(uuid.uuid4())
            repo = self.repo
            
            # Log metrics to DB
            repo.con.execute("""
                INSERT INTO code_profiling_logs 
                (execution_id, module_name, function_name, avg_execution_time_ms, peak_memory_mb, call_count, last_profiled)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, [execution_id, func.__module__, func.__name__, exec_time_ms, peak_mb, datetime.now()])
            
            # Flag non-linear bottlenecks (simple threshold for MVP)
            if exec_time_ms > 500:
                anomaly_id = str(uuid.uuid4())
                repo.con.execute("""
                    INSERT INTO identified_anomalies 
                    (anomaly_id, file_path, line_number, anomaly_type, severity, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW')
                """, [anomaly_id, func.__module__, 0, "O(N^2) LOOP", "CRITICAL", f"Function '{func.__name__}' took {exec_time_ms:.2f}ms"])
            
            return result
        return wrapper
    return decorator
