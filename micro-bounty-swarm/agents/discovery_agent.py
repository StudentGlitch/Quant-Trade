import asyncio
import uuid
import logging
import json
from playwright.async_api import async_playwright
import sys
from pathlib import Path
from urllib.request import urlopen

# Add core to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db_manager import add_bounty

logger = logging.getLogger("discovery_agent")
OBSCURA_HTTP_ENDPOINT = "http://127.0.0.1:9222/json/version"


def resolve_cdp_ws_endpoint() -> str:
    """Resolve the actual CDP websocket endpoint from the local Obscura/Chromium endpoint."""
    with urlopen(OBSCURA_HTTP_ENDPOINT, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
        ws_url = payload.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError("webSocketDebuggerUrl missing in CDP version response")
        return ws_url


def try_cdp_ws_endpoint() -> str | None:
    """Return CDP websocket URL if available, otherwise None."""
    try:
        return resolve_cdp_ws_endpoint()
    except Exception:
        return None

async def run_discovery():
    """Scrape GitHub and Upwork for micro-bounties using Obscura CDP."""
    logger.info("Starting Discovery Agent iteration...")
    
    async with async_playwright() as p:
        try:
            # Prefer external CDP if available; never auto-launch visible Edge windows.
            cdp_ws_endpoint = try_cdp_ws_endpoint()
            if cdp_ws_endpoint:
                browser = await p.chromium.connect_over_cdp(cdp_ws_endpoint)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
            else:
                logger.warning("CDP endpoint unavailable; using headless local Chromium fallback.")
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
            page = await context.new_page()
            
            # --- GitHub Scraping ("good first issue") ---
            github_url = "https://github.com/search?q=label%3A%22good+first+issue%22+state%3Aopen&type=issues"
            logger.info(f"Navigating to {github_url}")
            await page.goto(github_url, wait_until="networkidle", timeout=60000)
            
            # Extract basic issue info
            issues = await page.locator("div.search-title > a").all()
            for issue in issues[:5]: # Process top 5 per iteration
                url = await issue.get_attribute("href")
                if url:
                    full_url = f"https://github.com{url}"
                    # Use URL hash as ID to prevent duplicates
                    bounty_id = f"gh_{uuid.uuid5(uuid.NAMESPACE_URL, full_url).hex[:8]}"
                    title = await issue.inner_text()
                    
                    # Store in DB incrementally
                    add_bounty(
                        bounty_id=bounty_id,
                        platform="github",
                        url=full_url,
                        description=f"GitHub Issue: {title}",
                        reward_estimate=0.0 # Free/OSS bounty
                    )
                    logger.info(f"Discovered GitHub task: {bounty_id}")

            # --- Upwork RSS/Search logic would go here ---
            # Using similar Playwright locators. Handled with strict 
            # anti-goals (no CC, no heavy auth scraping without prior tokens).
            
        except Exception as e:
            logger.error(f"Discovery error: {e}")
        finally:
            if 'page' in locals():
                await page.close()
            if 'browser' in locals():
                await browser.close()

if __name__ == "__main__":
    asyncio.run(run_discovery())
