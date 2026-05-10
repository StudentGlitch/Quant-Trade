import os
import subprocess
import sys

def run_tests():
    """Dynamically discovers and executes tests in all sub-directories using uv run pytest."""
    test_suites = []
    # Directories to scan for tests
    scan_dirs = [
        'quant-engine', 
        'stockscope-unified', 
        'micro-bounty-swarm', 
        'StockscopeV2'
    ]

    print("--- Workspace Test Orchestrator: Starting Discovery ---")
    
    for root, dirs, files in os.walk('.'):
        # Exclude directories that are clearly non-Python test artifacts
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
        
        if 'tests' in dirs:
            test_dir = os.path.join(root, 'tests')
            test_suites.append(test_dir)

    if not test_suites:
        print("No test suites found.")
        sys.exit(0)

    failed = False
    for suite in test_suites:
        print(f"--- Running tests in: {suite} ---")
        try:
            # Execute pytest via uv
            result = subprocess.run(['uv', 'run', 'pytest', suite], capture_output=False)
            if result.returncode != 0:
                print(f"FAILED: {suite}")
                failed = True
        except Exception as e:
            print(f"Error executing tests in {suite}: {e}")
            failed = True

    if failed:
        print("--- CI/CD Validation FAILED ---")
        sys.exit(1)
    else:
        print("--- CI/CD Validation PASSED ---")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
