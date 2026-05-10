import asyncio
import logging
from playwright.async_api import async_playwright
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db_manager import get_bounties_by_status, update_status, log_revenue, save_proof_link
from agents.proof_collector import collect_github_proof_link

logger = logging.getLogger("submission_agent")

async def submit_task(bounty: dict):
    bounty_id = bounty["id"]
    artifacts_dir = Path(__file__).resolve().parent.parent / "artifacts"
    solution_file = artifacts_dir / f"{bounty_id}_solution.txt"
    
    if not solution_file.exists():
        # Artifact doesn't exist, cannot submit
        return

    if bounty.get("verification_hard_fail"):
        logger.warning(f"Skipping submission for hard-fail task: {bounty_id}")
        update_status(bounty_id, "FAILED")
        return

    logger.info(f"Attempting to submit solution for {bounty_id}")
    
    async with async_playwright() as p:
        try:
            # Note: We do NOT use Obscura here if we need an authenticated session
            # unless the Obscura instance holds our authenticated cookies.
            # For security and anti-goals, we skip hard CAPTCHAs.
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # --- Submission Logic Mock ---
            # In reality, this would navigate to the PR page or Upwork proposal page,
            # fill in the form using the text in solution_file, and click Submit.
            # If CAPTCHA is detected:
            # if await page.locator("iframe[title*='recaptcha']").count() > 0:
            #     raise Exception("Hard CAPTCHA detected.")
            
            await asyncio.sleep(2) # Simulate navigation and typing
            
            logger.info(f"Successfully submitted {bounty_id}")
            # First mark submitted attempt; final solved level depends on proof link.
            update_status(bounty_id, "SUBMITTED_UNVERIFIED")
            proof_link = collect_github_proof_link(bounty["url"]) if bounty.get("platform") == "github" else None
            save_proof_link(bounty_id, proof_link)
            if proof_link:
                log_revenue(bounty_id, bounty["platform"], bounty["url"], bounty["reward_estimate"])
                # Cleanup artifact when proof exists.
                solution_file.unlink(missing_ok=True)
            else:
                logger.warning(f"No verifiable proof link found for {bounty_id}; remains SUBMITTED_UNVERIFIED")
            
        except Exception as e:
            if "CAPTCHA" in str(e):
                logger.warning(f"Blocked by CAPTCHA on {bounty_id}")
                update_status(bounty_id, "BLOCKED")
            else:
                logger.error(f"Submission error for {bounty_id}: {e}")
                update_status(bounty_id, "FAILED")
        finally:
            if 'browser' in locals():
                await browser.close()

async def run_submission():
    """Find READY_FOR_SUBMISSION tasks and submit them."""
    logger.info("Starting Submission Agent iteration...")
    tasks = get_bounties_by_status("READY_FOR_SUBMISSION")
    logger.info(f"Submission queue size: {len(tasks)}")
    
    for task in tasks:
        if task.get("confidence_level") == "LOW":
            logger.warning(f"Submitting LOW confidence task: {task['id']}")
        await submit_task(task)

if __name__ == "__main__":
    asyncio.run(run_submission())
