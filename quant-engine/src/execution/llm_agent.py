import subprocess
import json
from loguru import logger
from pathlib import Path
from ..utils.json_utils import QuantJSONEncoder
from ..utils.contracts import LLMSynthesis
from pydantic import ValidationError

class LLMAgentCohort:
    """
    Acts as a Vibe-Enhanced Multi-Agent Swarm (inspired by HKUDS/Vibe-Trading).
    Simulates a team of experts including a Narrative/Vibe analyst.
    """
    def __init__(self):
        # PRD 4: Resolve absolute paths for hermes-agent (Bug Fix / v1.2 Scalable)
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.workspace_root = self.base_dir.parent
        
        self.hermes_python = self.workspace_root / "hermes-agent" / ".venv" / "Scripts" / "python.exe"
        self.hermes_cli = self.workspace_root / "hermes-agent" / "cli.py"
        self.recent_reflections = "No major mistakes recorded. Swarm is stable."

        if not self.hermes_python.exists():
            logger.error(f"Hermes Python not found at {self.hermes_python}")
        if not self.hermes_cli.exists():
            logger.error(f"Hermes CLI not found at {self.hermes_cli}")

    def _build_prompt(self, ticker: str, date: str, macro_context: dict, alt_context: dict, ml_signal: float, reflections: str) -> str:
        """Helper to construct the structured LLM prompt (Refactored by Jules)."""
        macro_str = json.dumps(macro_context, cls=QuantJSONEncoder)
        alt_str = json.dumps(alt_context, cls=QuantJSONEncoder)

        return (
            f"You are the CIO leading a Multi-Agent Swarm for {ticker} on {date}.\n\n"
            f"INPUTS:\n"
            f"- Statistical Momentum (ML): {ml_signal}\n"
            f"- Macro State: {macro_str}\n"
            f"- Retail Sentiment (Google/Wiki): {alt_str}\n"
            f"- Memory/Reflections: {reflections or self.recent_reflections}\n\n"
            f"TASK:\n"
            f"1. Conduct a brief 'Bull vs Bear Debate'. The Bull must argue for a Long position (+1.0) using the data. The Bear must argue for a Short position (-1.0).\n"
            f"2. Synthesize the debate, analyze the market regime, and provide a final macro-adjusted conviction signal from -1.0 (Strong Short) to 1.0 (Strong Long).\n\n"
            f"Respond ONLY with a valid JSON object matching exactly this schema:\n"
            f"{{\"bull_case\": \"<string>\", \"bear_case\": \"<string>\", \"synthesized_signal\": <float>}}"
        )

    def _parse_swarm_response(self, output: str, ml_signal: float, ticker: str, default_res: dict) -> dict:
        """Helper to parse and validate structured JSON from the LLM using Pydantic contracts."""
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].strip()

        try:
            response_data = json.loads(output)
            
            try:
                # Validate against Pydantic contract (PRD 5.2)
                synthesis = LLMSynthesis(**response_data)
                
                return {
                    "vibe": "Debate Completed", # Retained for compatibility with orchestrator
                    "final_signal": synthesis.synthesized_signal,
                    "chain_of_thought": f"BULL: {synthesis.bull_case} | BEAR: {synthesis.bear_case}"
                }
            except ValidationError as ve:
                logger.error(f"Pydantic Validation Error for {ticker}: {ve}")
                return default_res

        except json.JSONDecodeError:
            logger.error(f"Failed to parse swarm JSON for {ticker}. Raw: {output[:200]}")
            return default_res

    def get_signal_data(self, ticker: str, date: str, macro_context: dict, alt_context: dict, ml_signal: float, reflections: str = "") -> dict:
        """
        Query the Swarm for a collective signal and metadata using Vibe-to-Signal reasoning.
        """
        logger.info(f"Invoking Vibe-Enhanced Swarm + MiroFish Simulation for {ticker} on {date}...")

        prompt = self._build_prompt(ticker, date, macro_context, alt_context, ml_signal, reflections)

        default_res = {
            "vibe": "Unknown",
            "final_signal": ml_signal,
            "chain_of_thought": "Fallback to ML baseline due to agent error."
        }

        try:
            # Use absolute paths for the local hermes agent
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [str(self.hermes_python), str(self.hermes_cli), "-q", prompt],
                capture_output=True,
                text=True,
                encoding='utf-8',
                env=env,
                timeout=120
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return self._parse_swarm_response(output, ml_signal, ticker, default_res)
            else:
                logger.error(f"Hermes Swarm CLI error: {result.stderr}")
                return default_res
        except Exception as e:
            logger.error(f"Swarm execution failed for {ticker}: {e}")
            return default_res
