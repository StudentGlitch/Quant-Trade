import ast
import pandas as pd
from loguru import logger
import subprocess
import os
import re
from pathlib import Path

class DataEngineerAgent:
    """
    Phase 8.1: The Data Engineer Agent.
    Generates autonomous Playwright scrapers for OSINT data acquisition.
    """
    
    def __init__(self, scraper_dir: str = None):
        if scraper_dir is None:
            self.scraper_dir = Path(__file__).resolve().parent.parent / "data" / "autonomous_scrapers"
        else:
            self.scraper_dir = Path(scraper_dir)
            
        self.scraper_dir.mkdir(parents=True, exist_ok=True)

    def generate_scraper(self, dataset_id: str, target_url: str, description: str) -> dict:
        """Prompt Hermes to write a Playwright scraper for a specific dataset."""
        
        prompt = f"""
        ACT as a Senior Data Engineer. Write an ASYNCHRONOUS Python function using Playwright
        to scrape {description} from {target_url}.
        
        REQUIREMENTS:
        1. Function signature MUST be: async def scrape_data(page) -> pd.Series:
        2. The return MUST be a Pandas Series with a DatetimeIndex and numeric values.
        3. Use CSS selectors or XPath to find data. Handle common errors.
        4. Do NOT use external libraries besides pandas (pd), numpy (np), and playwright.
        5. Return ONLY the code block. No explanations.
        6. Implement a small sleep (await asyncio.sleep(2)) between actions to be polite.
        
        DATA REQUEST: {dataset_id} from {target_url}
        """
        
        logger.info(f"Data Engineer Agent: Prompting for autonomous scraper: {dataset_id}...")
        
        try:
            # Invoke Hermes (v1.2 absolute path mandate)
            process = subprocess.run(["python", "-m", "hermes_agent", "-z", "-q", prompt], 
                                    capture_output=True, text=True, encoding='utf-8')
            
            raw_code = process.stdout
            
            # Extract code
            code_match = re.search(r'```python\n(.*?)\n```', raw_code, re.DOTALL)
            code = code_match.group(1) if code_match else raw_code
            code = code.replace('```python', '').replace('```', '').strip()
            
            # Phase 8.1.3: AST Validation
            if self._is_safe(code):
                script_path = self.scraper_dir / f"{dataset_id}.py"
                with open(script_path, "w", encoding='utf-8') as f:
                    f.write("import pandas as pd\nimport numpy as np\nimport asyncio\n\n")
                    f.write(code)
                
                logger.success(f"Deployed autonomous scraper: {script_path}")
                return {"success": True, "path": str(script_path)}
            else:
                return {"success": False, "error": "AST Sandbox violation: Unauthorized system access attempted."}
                
        except Exception as e:
            logger.error(f"Scraper generation failed for {dataset_id}: {e}")
            return {"success": False, "error": str(e)}

    def _is_safe(self, code_str: str) -> bool:
        """Strict AST parsing to prevent system-level execution (PRD 4.3 / 5.3)."""
        try:
            tree = ast.parse(code_str)
            
            # Explicitly forbidden modules for ETL scrapers
            forbidden_modules = {'os', 'sys', 'subprocess', 'shutil', 'builtins', 'socket', 'pickle', 'requests'}
            forbidden_names = {'exec', 'eval', 'getattr', 'setattr', '__import__', 'open'}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in forbidden_modules:
                            logger.error(f"ETL Sandbox Violation: Forbidden import '{alias.name}'")
                            return False
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in forbidden_modules:
                        logger.error(f"ETL Sandbox Violation: Forbidden import-from '{node.module}'")
                        return False
                        
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                        logger.error(f"ETL Sandbox Violation: Forbidden call '{node.func.id}()'")
                        return False
                        
            return True
        except Exception as e:
            logger.error(f"AST Parsing error: {e}")
            return False
