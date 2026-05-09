import psutil
import os
import sys
from loguru import logger

def kill_zombie_locks(db_path: str = None):
    """
    Finds and terminates other Python processes running the quant engine 
    to release potential DuckDB file locks (PRD Bug Fix).
    """
    current_pid = os.getpid()
    target_scripts = ['swarm_daemon.py', 'orchestrator.py']
    
    logger.info("Running pre-flight Zombie Sweeper...")
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            info = proc.info
            pid = info['pid']
            cmdline = info['cmdline']
            
            if pid == current_pid:
                continue
                
            if not cmdline:
                continue
                
            # Check if this is a python process running our scripts
            is_python = 'python' in info['name'].lower() or 'python' in cmdline[0].lower()
            if is_python:
                cmd_str = " ".join(cmdline)
                if any(script in cmd_str for script in target_scripts):
                    logger.warning(f"Found zombie process {pid} holding lock: {cmd_str}. Terminating...")
                    proc.terminate()
                    # Wait briefly for termination
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        logger.error(f"Process {pid} refused to terminate. Killing forcefully...")
                        proc.kill()
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    logger.info("Zombie Sweeper complete.")
