import os
import uuid
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path
from loguru import logger
from datetime import datetime
from src.data.duckdb_repo import DuckDBRepo

class VisionAnalyst:
    """PDF chart extraction and OCR perception using pytesseract."""

    def __init__(self, repo: DuckDBRepo, tesseract_cmd: str = None):
        self.repo = repo
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def analyze_presentation(self, ticker: str, pdf_path: str):
        """Convert PDF slides to images, run OCR, and summarize insights."""
        logger.info(f"Analyzing investor presentation for {ticker}: {pdf_path}")
        
        try:
            # 1. Convert PDF pages to list of images
            images = convert_from_path(pdf_path, dpi=200)
            
            for i, image in enumerate(images):
                # 2. OCR on each page
                extracted_text = pytesseract.image_to_string(image)
                
                # 3. Autonomous Insight (Mock LLM Summarization for V1)
                # In production, this OCR text goes to Hermes LLM
                visual_summary = self._generate_visual_summary(extracted_text)
                
                image_id = str(uuid.uuid4())
                
                # 4. Store in DuckDB
                self.repo.con.execute("""
                    INSERT INTO vision_perception_ledger 
                    (image_id, ticker, date, source_document, extracted_text, visual_insight_summary, bullish_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [image_id, ticker, datetime.now().date(), os.path.basename(pdf_path), extracted_text, visual_summary, 0.5])
                
                logger.info(f"Analyzed slide {i+1} for {ticker}")

        except Exception as e:
            logger.error(f"Vision analysis failed for {pdf_path}: {e}")
            raise

    def _generate_visual_summary(self, text: str) -> str:
        """Heuristic-based visual summary (placeholder for LLM logic)."""
        if not text.strip():
            return "No text detected on this slide."
        
        # Simple extraction logic for demo
        lines = text.split('\n')
        key_lines = [l.strip() for l in lines if len(l.strip()) > 10][:3]
        summary = "AUTONOMOUS VISION INSIGHT: " + " | ".join(key_lines)
        return summary
