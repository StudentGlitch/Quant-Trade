SOLVED_LEVEL = "L3"

RESOLUTION_LEVELS = {
    "L1": "Artifact generated",
    "L2": "Artifact passed deterministic quality checks",
    "L3": "Submission has verifiable proof link",
    "L4": "External acceptance confirmed (future extension)",
}

# Deterministic verifier rubric weights.
RUBRIC = {
    "non_empty_artifact": 0.35,
    "actionable_content": 0.25,
    "task_context_reference": 0.20,
    "no_runtime_error_text": 0.20,
}

# Hard-fail means the task should not proceed to submission.
HARD_FAIL_MIN_LENGTH = 30
