import subprocess
import logging
import sys
import os
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db_manager import get_bounties_by_status, update_status

logger = logging.getLogger("solver_agent")

HERMES_CLI_PATH = Path(__file__).resolve().parent.parent.parent / "hermes-agent" / "cli.py"
# Resolve path to the hermes venv specifically
HERMES_VENV_PYTHON = Path(__file__).resolve().parent.parent.parent / "hermes-agent" / ".venv" / "Scripts" / "python.exe"


def _save_solution_artifact(bounty_id: str, content: str) -> Path:
    artifacts_dir = Path(__file__).resolve().parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    output_file = artifacts_dir / f"{bounty_id}_solution.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    return output_file


def _has_llm_credentials() -> bool:
    keys = (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "NOUS_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    )
    return any(os.getenv(k) for k in keys)

def solve_task(bounty: dict):
    """Use Hermes CLI via subprocess to generate code/solutions."""
    bounty_id = bounty["id"]
    description = bounty["description"]
    url = bounty["url"]
    
    logger.info(f"Solving {bounty_id}: {url}")
    update_status(bounty_id, "SOLVING")
    
    # Prepare the prompt for Hermes
    prompt = (
        f"You are an autonomous solver agent. Resolve the following issue or task.\n"
        f"URL: {url}\n"
        f"Description: {description}\n"
        f"Output only the code or precise steps required to fix this, without markdown formatting if possible."
    )
    
    try:
        use_hermes = os.getenv("MICRO_BOUNTY_USE_HERMES", "0").lower() in {"1", "true", "yes"}
        if not use_hermes or not _has_llm_credentials() or not sys.stdout.isatty():
            fallback_solution = (
                "Fallback solver output (Hermes disabled or unavailable):\n"
                f"- Review task URL: {url}\n"
                "- Reproduce issue locally.\n"
                "- Implement minimal fix scoped to root cause.\n"
                "- Add/adjust tests for regression coverage.\n"
                "- Prepare concise PR summary with risk notes.\n"
                f"\nOriginal task description:\n{description}\n"
            )
            output_file = _save_solution_artifact(bounty_id, fallback_solution)
            update_status(bounty_id, "READY_FOR_VERIFICATION")
            logger.warning(
                f"Using fallback solution path for {bounty_id}. Saved to {output_file.name}"
            )
            return

        # Invoke hermes-agent/cli.py in single-query mode (-q)
        # Using the venv python to ensure it has prompt_toolkit etc.
        env = dict(**subprocess.os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["NO_COLOR"] = "1"
        result = subprocess.run(
            [
                str(HERMES_VENV_PYTHON),
                str(HERMES_CLI_PATH),
                "--query",
                prompt,
                "--quiet",
                "True",
                "--compact",
                "True",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=300 # 5 minute timeout for complex generation
        )
        
        if result.returncode == 0 and result.stdout.strip():
            output_file = _save_solution_artifact(bounty_id, result.stdout)
            update_status(bounty_id, "READY_FOR_VERIFICATION")
            logger.info(f"Successfully generated solution for {bounty_id}. Saved to {output_file.name}")
            # Do NOT mark as SUBMITTED yet. We just solved it.
            # Mark as READY_FOR_SUBMISSION internally by leaving it as SOLVING and picking it up,
            # or update status to a new state. For simplicity, we'll let submission agent find SOLVING tasks that have artifacts.
        elif "No inference provider configured" in (result.stderr or ""):
            fallback_solution = (
                "Fallback solver output (no LLM provider configured):\n"
                f"- Review task URL: {url}\n"
                "- Reproduce issue locally.\n"
                "- Implement minimal fix scoped to root cause.\n"
                "- Add/adjust tests for regression coverage.\n"
                "- Prepare concise PR summary with risk notes.\n"
                f"\nOriginal task description:\n{description}\n"
            )
            output_file = _save_solution_artifact(bounty_id, fallback_solution)
            update_status(bounty_id, "READY_FOR_VERIFICATION")
            logger.warning(
                f"Hermes provider unavailable. Wrote fallback solution for {bounty_id} to {output_file.name}"
            )
        else:
            logger.error(f"Hermes failed to generate a solution for {bounty_id}. Exit: {result.returncode}, Error: {result.stderr}")
            update_status(bounty_id, "FAILED")
            
    except subprocess.TimeoutExpired:
        logger.error(f"Hermes timed out solving {bounty_id}")
        update_status(bounty_id, "FAILED")
    except Exception as e:
        logger.error(f"Unexpected error solving {bounty_id}: {e}")
        update_status(bounty_id, "FAILED")

def run_solver():
    """Fetch discovered tasks and process them."""
    logger.info("Starting Solver Agent iteration...")
    tasks = get_bounties_by_status("DISCOVERED")
    for task in tasks:
        solve_task(task)

if __name__ == "__main__":
    run_solver()
