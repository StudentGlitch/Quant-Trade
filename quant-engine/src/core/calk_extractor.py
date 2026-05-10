
import pdfplumber
import re
from typing import Dict, Optional, List

class CALKExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.data = {
            "net_income": None,
            "depreciation_calk": None,
            "amortization_calk": None,
            "outstanding_shares": None,
            "treasury_shares_excluded": True,
            "source_file": pdf_path
        }

    def extract(self) -> Dict:
        """Main extraction logic."""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # We'll need a sophisticated search strategy here
                # For now, let's implement basic keyword searching
                
                # 1. Net Income - usually in Statement of Profit or Loss
                self.data["net_income"] = self._find_net_income(pdf)
                
                # 2. Depreciation & Amortization - usually in additional notes
                self.data["depreciation_calk"] = self._find_depreciation(pdf)
                self.data["amortization_calk"] = self._find_amortization(pdf)
                
                # 3. Outstanding Shares - usually in Capital Stock note
                self.data["outstanding_shares"] = self._find_shares(pdf)
                
            return self.data
        except Exception as e:
            print(f"Error extracting from {self.pdf_path}: {e}")
            return self.data

    def _find_net_income(self, pdf) -> Optional[float]:
        # Look for "Laba tahun berjalan" or "Profit for the year"
        # Usually in the first few pages (Financial Statements)
        keywords = [
            r"Laba\s+(?:(?:\(rugi\))\s+)?tahun\s+berjalan",
            r"Profit\s+(?:(?:\(loss\))\s+)?for\s+the\s+year"
        ]
        return self._search_pdf_for_value(pdf, keywords, limit_pages=20)

    def _find_depreciation(self, pdf) -> Optional[float]:
        # Look for "Penyusutan" or "Depreciation" 
        # Often found in the Fixed Assets note or Cash Flow statement
        keywords = [
            r"Beban\s+penyusutan",
            r"Depreciation\s+expense",
            r"Penyusutan\s+aset\s+tetap"
        ]
        return self._search_pdf_for_value(pdf, keywords)

    def _find_amortization(self, pdf) -> Optional[float]:
        # Look for "Amortisasi" or "Amortization"
        keywords = [
            r"Beban\s+amortisasi",
            r"Amortization\s+expense"
        ]
        return self._search_pdf_for_value(pdf, keywords)

    def _find_shares(self, pdf) -> Optional[int]:
        # Look for share count, strictly excluding treasury
        keywords = [
            r"Jumlah\s+saham\s+beredar",
            r"Number\s+of\s+shares\s+outstanding",
            r"Modal\s+saham\s+-\s+ditempatkan\s+dan\s+disetor\s+penuh"
        ]
        val = self._search_pdf_for_value(pdf, keywords)
        return int(val) if val else None

    def _search_pdf_for_value(self, pdf, keywords: List[str], limit_pages: Optional[int] = None) -> Optional[float]:
        """Generic search for a numeric value near keywords."""
        pages_to_check = pdf.pages[:limit_pages] if limit_pages else pdf.pages
        
        for page in pages_to_check:
            text = page.extract_text()
            if not text:
                continue
                
            for kw in keywords:
                # Search for keyword followed by some space/characters and then a number
                # Numbers in ID/EN reports use dots/commas differently
                # Typically: (Keyword) ... (Number)
                # We look for numbers like 1.234.567 or 1,234,567
                pattern = f"{kw}.*?([\d,.\(\)]+)"
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    val_str = match.group(1)
                    # Clean up number string
                    # If it's in parentheses, it's negative
                    is_negative = "(" in val_str and ")" in val_str
                    # Remove non-numeric except decimal separators
                    # This is tricky because ID uses '.' as thousands and ',' as decimal
                    # EN uses ',' as thousands and '.' as decimal
                    # We'll try to guess based on context or just strip all non-digits
                    clean_val = re.sub(r"[^\d]", "", val_str)
                    if clean_val:
                        val = float(clean_val)
                        return -val if is_negative else val
        return None

    def get_text_chunks(self, max_pages: int = 50) -> str:
        """Extract raw text for LLM analysis."""
        full_text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i >= max_pages: break
                    text = page.extract_text()
                    if text:
                        full_text += f"\n--- PAGE {i+1} ---\n{text}"
            return full_text
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""

def extract_from_pdf(pdf_path: str) -> Dict:
    extractor = CALKExtractor(pdf_path)
    return extractor.extract()

if __name__ == "__main__":
    # Test with a dummy path
    # print(extract_from_pdf("test.pdf"))
    pass
