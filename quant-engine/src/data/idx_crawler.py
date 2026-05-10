import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from loguru import logger
from .ticker_validator import normalize_ticker

class IDXCrawler:
    """Autonomous Discovery using Playwright and Obscura CDP (PRD Phase 0.1)."""
    
    CDP_URL = "http://127.0.0.1:9222"
    
    async def run_discovery(self) -> dict:
        """Scrape Wikipedia/IDX for current LQ45 and IDX30 constituents."""
        logger.info("Starting Autonomous Discovery Phase...")
        universe = {
            'LQ45': set(),
            'IDX30': set()
        }
        
        async with async_playwright() as p:
            try:
                # PRD 0.1.1: Connect to Obscura CDP
                logger.info(f"Connecting to Obscura CDP at {self.CDP_URL}")
                browser = await p.chromium.connect_over_cdp(self.CDP_URL)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
                
                # 1. Scrape LQ45
                logger.info("Scraping LQ45 constituents...")
                await page.goto("https://en.wikipedia.org/wiki/LQ45", wait_until="domcontentloaded", timeout=60000)
                html = await page.content()
                soup = BeautifulSoup(html, 'lxml')
                
                # Find the main table (usually the first one with class 'wikitable')
                table = soup.find('table', {'class': 'wikitable'})
                if table:
                    rows = table.find_all('tr')[1:] # Skip header
                    for row in rows:
                        cols = row.find_all('td')
                        if cols:
                            # Typically the first or second column is the ticker
                            raw_ticker = cols[0].text.strip()
                            # Clean and format
                            clean_ticker = normalize_ticker(raw_ticker)
                            if clean_ticker.endswith(".JK"):
                                universe['LQ45'].add(clean_ticker)
                
                logger.info(f"Discovered {len(universe['LQ45'])} LQ45 tickers.")
                
            except Exception as e:
                logger.error(f"Discovery failed: {e}. Falling back to default lists if available.")
            finally:
                if 'page' in locals():
                    await page.close()
                if 'browser' in locals():
                    await browser.close()
                    
        return universe

if __name__ == "__main__":
    crawler = IDXCrawler()
    res = asyncio.run(crawler.run_discovery())
    print(res)
