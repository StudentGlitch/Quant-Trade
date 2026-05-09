
import os
import json
from loguru import logger
from typing import List, Dict, Optional
from scrapegraphai.graphs import SmartScraperGraph
from ..utils.json_utils import QuantJSONEncoder

class ScrapeGraphClient:
    """
    Intelligent Web Scraper (powered by ScrapeGraphAI).
    Extracts structured data from any website using LLM-guided graph logic.
    """

    def __init__(self, api_key: str = None, model: str = "openai/gpt-4o-mini"):
        # Use provided key or read from environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        # Configuration for ScrapeGraphAI
        self.config = {
            "llm": {
                "api_key": self.api_key,
                "model": self.model,
            },
            "verbose": True,
            "headless": True,
        }

    def scrape_url(self, url: str, prompt: str) -> Optional[Dict]:
        """
        Scrape a specific URL with a natural language prompt.
        """
        if not self.api_key:
            logger.debug(f"No API key provided for ScrapeGraphAI. Skipping scrape for {url}.")
            return {}

        logger.info(f"Scraping {url} with prompt: '{prompt}'...")
        try:
            smart_scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=self.config
            )
            result = smart_scraper.run()
            logger.success(f"Scrape successful for {url}")
            return result
        except Exception as e:
            logger.error(f"ScrapeGraphAI error for {url}: {e}")
            return None

    def get_ticker_sentiment(self, ticker: str) -> Optional[Dict]:
        """
        Example use case: Scrape Yahoo Finance News for a ticker and get sentiment.
        """
        ticker_clean = ticker.split('.')[0]
        url = f"https://finance.yahoo.com/quote/{ticker}/news"
        prompt = (
            f"Extract the top 5 news headlines for {ticker_clean}. "
            f"For each headline, provide a sentiment score from -1.0 (very negative) to 1.0 (very positive)."
        )
        
        return self.scrape_url(url, prompt)

if __name__ == "__main__":
    # Test (requires API key)
    # client = ScrapeGraphClient()
    # print(client.get_ticker_sentiment("BBCA.JK"))
    print("ScrapeGraphClient ready.")
