import ast
import pandas as pd
from loguru import logger
import subprocess
import os
import re

class AlphaResearcher:
    """
    Phase 5.1: The Alpha Researcher Agent.
    Generates novel Alpha factors via LLM and validates code safety via AST.
    """
    
    def __init__(self):
        # We invoke the hermes-agent via CLI to get fresh context each time
        self.hermes_cmd = ["python", "-m", "hermes_agent", "-z", "-q"]

    def generate_novel_alpha(self, available_osint: list[str] = None) -> dict:
        """Instruction loop to generate a novel Python factor."""
        osint_context = ""
        if available_osint:
            osint_context = f"\nAVAILABLE OSINT DATASETS: {', '.join(available_osint)}. You can use these columns from the dataframe."

        prompt = f"""
        ACT as a Senior Quantitative Researcher. Write a NOVEL mathematical alpha factor 
        using Pandas, OHLCV data, and available alternative datasets. 
        
        {osint_context}

        REQUIREMENTS:
        1. Output pure Python code wrapping the logic in this exact signature:
           def generate_alpha(df: pd.DataFrame) -> pd.Series:
        2. Use indicators like rolling means, std, momentum, or correlations.
        3. Do NOT use external libraries besides pandas (pd) and numpy (np).
        4. Return ONLY the code block.
        
        Example idea: (close / feat_newcastle_coal_usd.rolling(20).mean()) - 1
        """
        
        logger.info("Alpha Researcher: Prompting Hermes Swarm for a novel signal...")
        try:
            # Note: Using absolute path resolution logic from core mandates
            process = subprocess.run(["python", "-m", "hermes_agent", "-z", "-q", prompt], 
                                    capture_output=True, text=True, encoding='utf-8')
            
            raw_code = process.stdout
            
            # Extract code between ```python and ```
            code_match = re.search(r'```python\n(.*?)\n```', raw_code, re.DOTALL)
            code = code_match.group(1) if code_match else raw_code
            
            # Clean common LLM formatting issues
            code = code.replace('```python', '').replace('```', '').strip()
            
            if self._is_safe(code):
                return {"success": True, "code": code, "id": f"alpha_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"}
            else:
                return {"success": False, "error": "AST Sandbox violation detected."}
                
        except Exception as e:
            logger.error(f"Alpha Researcher failed: {e}")
            return {"success": False, "error": str(e)}

    def _is_safe(self, code_str: str) -> bool:
        """
        Phase 5.1.3: AST Sandbox.
        Rejects any code containing malicious imports or execution vectors.
        """
        try:
            tree = ast.parse(code_str)
            
            forbidden_modules = {'os', 'sys', 'subprocess', 'requests', 'builtins', 'socket', 'pickle'}
            forbidden_names = {'exec', 'eval', 'getattr', 'setattr', '__import__', 'open'}
            
            for node in ast.walk(tree):
                # Check for imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in forbidden_modules:
                            logger.error(f"Sandbox Violation: Forbidden import '{alias.name}'")
                            return False
                if isinstance(node, ast.ImportFrom):
                    if node.module in forbidden_modules:
                        logger.error(f"Sandbox Violation: Forbidden import-from '{node.module}'")
                        return False
                        
                # Check for direct calls to forbidden functions
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                        logger.error(f"Sandbox Violation: Forbidden call '{node.func.id}()'")
                        return False
                        
            logger.info("AST Sandbox: Code verified as safe.")
            return True
        except Exception as e:
            logger.error(f"AST Parsing failed: {e}")
            return False
