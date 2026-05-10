import os
import csv
import logging
import time
import argparse
import json
import pathlib
import re
import fitz  # PyMuPDF
import pytesseract
import pdf2image
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- Configuration & Setup ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Use relative paths from script directory
SCRIPT_DIR = pathlib.Path(__file__).parent
ROOT_PATH = SCRIPT_DIR / "Data 2020-2023 Consumer Non Cyclical"
OUTPUT_CSV = SCRIPT_DIR / "Extracted_Financial_Data.csv"
LOG_FILE = SCRIPT_DIR / "logs" / "extraction_errors.log"

# Create logs directory if it doesn't exist
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Models ---
class FinancialData(BaseModel):
    ticker: str
    year: int
    TotalAset: Optional[int] = None
    TotalLiabilitas: Optional[int] = None
    TotalCurrentAssets: Optional[int] = None
    TotalCurrentLiabilities: Optional[int] = None
    NetIncome: Optional[int] = None
    OperatingCashFlow: Optional[int] = None
    RetainedEarning: Optional[int] = None
    EBIT: Optional[int] = None
    Sales: Optional[int] = None
    Depreciation: Optional[int] = None
    Amortization: Optional[int] = None
    OutstandingShares: Optional[int] = None
    HasStockSplit: bool

# --- PDF Processing ---
KEYWORDS = [
    "LAPORAN POSISI KEUANGAN", "STATEMENT OF FINANCIAL POSITION",
    "STATEMENT OF CASH FLOWS", "LAPORAN ARUS KAS",
    "ASET TETAP", "FIXED ASSETS",
    "ASET TAK BERWUJUD", "INTANGIBLE ASSETS",
    "PEMECAHAN SAHAM", "STOCK SPLIT"
]

def prune_pdf(pdf_path: pathlib.Path) -> str:
    """Intelligently prune PDF to relevant pages and extract text using Hybrid OCR approach."""
    try:
        doc = fitz.open(str(pdf_path))
        relevant_pages = set()
        page_texts = {}
        
        logger.info(f"Scanning {pdf_path.name} ({len(doc)} pages)...")

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            # OCR Fallback Logic: If text is suspiciously low, attempt OCR
            if len(text.strip()) < 150:
                try:
                    # Convert single page to image for OCR
                    images = pdf2image.convert_from_path(str(pdf_path), first_page=page_num+1, last_page=page_num+1, dpi=300)
                    if images:
                        ocr_text = pytesseract.image_to_string(images[0], lang='eng+ind')
                        if len(ocr_text.strip()) > len(text.strip()):
                            text = ocr_text
                except Exception as ocr_err:
                    # Log but continue with native text if OCR fails (might be due to missing binaries)
                    logger.warning(f"OCR fallback failed for {pdf_path.name} page {page_num+1}: {ocr_err}")
            
            page_texts[page_num] = text
            text_upper = text.upper()
            
            if any(kw in text_upper for kw in KEYWORDS):
                relevant_pages.add(page_num)
                if page_num > 0: relevant_pages.add(page_num - 1)
                if page_num < len(doc) - 1: relevant_pages.add(page_num + 1)
        
        extracted_text = []
        for p_num in sorted(list(relevant_pages)):
            extracted_text.append(page_texts.get(p_num, ""))
        
        doc.close()
        return "\n--- PAGE ---\n".join(extracted_text)
    except Exception as e:
        logger.error(f"Error pruning PDF {pdf_path}: {e}")
        return ""

# --- GenAI API ---
MODELS = ['gemini-2.0-flash-lite', 'gemini-2.0-flash', 'gemini-flash-latest']
BACKOFF_INTERVALS = [30, 60, 120]

SYSTEM_PROMPT = """
You are a specialized financial analyst extracting data from Indonesian annual reports.
Your task is to populate the provided JSON schema based on the extracted text.

STRICT ACCOUNTING LOGIC:
1. For 'NetIncome', you MUST strictly use 'Profit for the year' (Laba Tahun Berjalan).
2. For 'Depreciation', locate the 'Fixed Assets' (Aset Tetap) section in the Notes (CALK) and extract the 'additions' (penambahan) for depreciation.
3. For 'Amortization', locate the 'Intangible Assets' (Aset Tak Berwujud) section in the Notes (CALK) and extract its amortization.
4. For 'OutstandingShares', the nominal value MUST explicitly exclude Treasury Stocks (Saham Treasuri).
5. If the document indicates the company performed a Stock Split (Pemecahan Saham) during this period, set 'HasStockSplit' to true.
6. All financial values should be in their absolute Rupiah values if possible (multiply by millions/billions if the report specifies 'in millions/billions').
"""

def call_genai_with_backoff(ticker: str, year: int, text: str):
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found in environment.")
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    # prompt to be used
    prompt = f"Extract financial data for {ticker} in year {year} from the following text:\n\n{text[:40000]}"

    for model_name in MODELS:
        for attempt, delay in enumerate(BACKOFF_INTERVALS + [None]):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type='application/json',
                        response_schema=FinancialData,
                    )
                )
                return response.parsed
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "ResourceExhausted" in err_msg:
                    if delay:
                        logger.warning(f"Rate limit hit for {ticker} {year} using {model_name}. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit hit for {ticker} {year} using {model_name}. No more retries for this model.")
                else:
                    logger.error(f"Error calling API for {ticker} {year} using {model_name}: {e}")
                    break
    return None

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Financial Data Extraction Pipeline - Phase 4")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of PDFs processed")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in .env file.")
        return

    # Prepare CSV
    headers = [
        "ticker", "year", "TotalAset", "TotalLiabilitas", "TotalCurrentAssets",
        "TotalCurrentLiabilities", "NetIncome", "OperatingCashFlow",
        "RetainedEarning", "EBIT", "Sales", "Depreciation", "Amortization", "OutstandingShares"
    ]
    
    file_exists = OUTPUT_CSV.exists()
    
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()

        processed_count = 0
        
        # Traverse directory
        for ticker_dir in ROOT_PATH.iterdir():
            if not ticker_dir.is_dir():
                continue
            
            ticker = ticker_dir.name
            
            for pdf_file in ticker_dir.glob("*.pdf"):
                if args.limit and processed_count >= args.limit:
                    logger.info(f"Limit of {args.limit} reached. Stopping.")
                    return

                # Extract year from filename
                years_found = re.findall(r"\b202\d\b", pdf_file.name)
                if not years_found:
                    logger.warning(f"Could not determine year for {pdf_file.name}. Skipping.")
                    continue
                
                year = int(years_found[-1])

                logger.info(f"--- Starting Processing: {ticker} {year} ---")
                
                text = prune_pdf(pdf_file)
                if not text:
                    logger.warning(f"No relevant text extracted (native or OCR) for {ticker} {year}. Skipping.")
                    continue
                
                data = call_genai_with_backoff(ticker, year, text)
                
                if data:
                    if data.HasStockSplit:
                        logger.warning(f"Excluding {ticker} {year} due to Stock Split detection.")
                    else:
                        row = data.model_dump()
                        row.pop("HasStockSplit")
                        writer.writerow(row)
                        f.flush()
                        logger.info(f"Successfully saved data for {ticker} {year}.")
                else:
                    logger.error(f"Failed to process {ticker} {year} after all API attempts.")

                processed_count += 1
                time.sleep(15)

if __name__ == "__main__":
    main()
