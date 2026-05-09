import subprocess
import json
from pathlib import Path
from loguru import logger
from ..utils.json_utils import QuantJSONEncoder

class LLMAgentCohort:
    """
    Acts as a Vibe-Enhanced Multi-Agent Swarm (inspired by HKUDS/Vibe-Trading).
    Simulates a team of experts including a Narrative/Vibe analyst.
    1. The Narrative Analyst: Interprets 'vibes' from Google Trends and retail spikes.
    2. The Value Contrarian: Challenges momentum if indicators look overextended.
    3. The Growth Maximizer: Capitalizes on retail attention and trend continuation.
    4. The Risk Sentinel: Monitors macro fragility (Yield Curve, VIX).
    """
    def __init__(self):
        # Resolve path to the hermes agent
        pass # Paths removed to use python -m
        self.recent_reflections = "No major mistakes recorded. Swarm is stable."

    def get_signal_data(self, ticker: str, date: str, macro_context: dict, alt_context: dict, ml_signal: float, reflections: str = "") -> dict:
        """
        Query the Swarm for a collective signal and metadata using Vibe-to-Signal reasoning.
        """
        logger.info(f"Invoking Vibe-Enhanced Swarm + MiroFish Simulation for {ticker} on {date}...")
        
        # PRD Bug Fix: Safely serialize context using QuantJSONEncoder
        macro_str = json.dumps(macro_context, cls=QuantJSONEncoder)
        alt_str = json.dumps(alt_context, cls=QuantJSONEncoder)

        prompt = (
            f"You are the CIO leading a Multi-Agent Swarm for {ticker} on {date}.\n\n"
            f"INPUTS:\n"
            f"- Statistical Momentum (ML): {ml_signal}\n"
            f"- Macro State: {macro_str}\n"
            f"- Retail Sentiment (Google/Wiki): {alt_str}\n"
            f"- Memory/Reflections: {reflections or self.recent_reflections}\n\n"
            f"TASK:\n"
            f"1. VIBE ANALYSIS: Have 'The Narrative Analyst' identify the current market 'vibe' (e.g., FOMO, Panic, Boring, Regime Shift).\n"
            f"2. PERSONA DEBATE: Generate brief conflicting views from 'The Value Contrarian', 'The Growth Maximizer', and 'The Risk Sentinel'.\n"
            f"3. MIROFISH SIMULATION: Rehearse 3 parallel scenarios (Bull/Bear/Sideways) with probabilities.\n"
            f"4. FINAL SYNTHESIS: Provide a conviction signal (-1.0 to 1.0) and include your detailed 'Chain of Thought'.\n\n"
            f"Respond ONLY with valid JSON: {{\"vibe\": \"<string>\", \"swarm_views\": {{...}}, \"simulation\": {{...}}, \"final_signal\": <float>, \"chain_of_thought\": \"...\"}}"
        )

        default_res = {
            "vibe": "Unknown",
            "final_signal": ml_signal,
            "chain_of_thought": "Fallback to ML baseline due to agent error."
        }

        try:
            result = subprocess.run(
                ["python", "-m", "hermes_agent", "-q", prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "```json" in output:
                    output = output.split("```json")[1].split("```")[0].strip()
                elif "```" in output:
                    output = output.split("```")[1].strip()
                
                try:
                    response_data = json.loads(output)
                    return {
                        "vibe": response_data.get('vibe', 'Unknown'),
                        "final_signal": float(response_data.get('final_signal', ml_signal)),
                        "chain_of_thought": response_data.get('chain_of_thought', 'No reasoning provided.')
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse swarm JSON for {ticker}. Raw: {output[:200]}")
                    return default_res
            else:
                logger.error(f"Hermes Swarm CLI error: {result.stderr}")
                return default_res
        except Exception as e:
            logger.error(f"Swarm execution failed for {ticker}: {e}")
            return default_res
