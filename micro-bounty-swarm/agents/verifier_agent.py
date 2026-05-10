import sys
import logging
import time
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db_manager import (
    get_bounties_by_status,
    update_status,
    save_verification_result,
    record_verifier_run,
)
from core.success_criteria import RUBRIC, HARD_FAIL_MIN_LENGTH

logger = logging.getLogger("verifier_agent")

def verify_solution(bounty: dict):
    """Verify generated code against a rubric."""
    bounty_id = bounty["id"]
    artifacts_dir = Path(__file__).resolve().parent.parent / "artifacts"
    solution_file = artifacts_dir / f"{bounty_id}_solution.txt"
    
    if not solution_file.exists():
        logger.warning(f"Skipping verification for {bounty_id}: artifact missing")
        return False

    logger.info(f"Verifying solution for {bounty_id}")
    update_status(bounty_id, "VERIFYING")
    
    with open(solution_file, "r", encoding="utf-8") as f:
        solution = f.read()

    # Deterministic rubric:
    # - non_empty_artifact
    # - actionable_content
    # - task_context_reference
    # - no_runtime_error_text
    score = 0.0
    notes = []
    hard_fail = False
    reasons = []

    if len(solution.strip()) < HARD_FAIL_MIN_LENGTH:
        hard_fail = True
        reasons.append("artifact-too-short")
    else:
        score += RUBRIC["non_empty_artifact"]
        notes.append("Non-empty artifact.")

    actionable_markers = ("fix", "patch", "implement", "update", "steps", "code", "def ", "class ")
    if any(marker in solution.lower() for marker in actionable_markers):
        score += RUBRIC["actionable_content"]
        notes.append("Actionable content detected.")
    else:
        reasons.append("no-actionable-content")

    if bounty["url"] in solution or bounty["id"] in solution:
        score += RUBRIC["task_context_reference"]
        notes.append("Task context referenced.")
    else:
        reasons.append("no-task-context-reference")

    if "traceback" not in solution.lower() and "error:" not in solution.lower():
        score += RUBRIC["no_runtime_error_text"]
        notes.append("No runtime error text.")
    else:
        reasons.append("runtime-error-text-present")

    if "fallback solver output" in solution.lower():
        reasons.append("fallback-output")

    confidence = "LOW"
    if score >= 0.8:
        confidence = "HIGH"
    elif score >= 0.5:
        confidence = "MEDIUM"

    reason_text = "; ".join(reasons) if reasons else "verification-pass"
    save_verification_result(
        bounty_id=bounty_id,
        score=score,
        notes="; ".join(notes),
        confidence_level=confidence,
        hard_fail=hard_fail,
        reason=reason_text,
    )
    if hard_fail:
        update_status(bounty_id, "FAILED")
        return False
    update_status(bounty_id, "READY_FOR_SUBMISSION")
    return True

def run_verifier():
    """Pick up SOLVING tasks that have artifacts and verify them."""
    started = time.perf_counter()
    tasks = get_bounties_by_status("READY_FOR_VERIFICATION")
    queue_size = len(tasks)
    logger.info(f"Starting Verifier Agent iteration... queue_size={queue_size}")

    processed = 0
    failed = 0
    for task in tasks:
        ok = verify_solution(task)
        processed += 1
        if not ok:
            failed += 1

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Verifier iteration summary: "
        f"queue_size={queue_size}, processed={processed}, failed={failed}, elapsed_ms={elapsed_ms}"
    )
    record_verifier_run(
        queue_size=queue_size,
        processed_count=processed,
        failed_count=failed,
        elapsed_ms=elapsed_ms,
    )

if __name__ == "__main__":
    run_verifier()
