"""
crawler_v2/evaluator/self_eval.py — Self-evaluation and comparison between
v1 and v2 crawlers (Phase 8).

Generates scores using the same rubric as v1 but with a higher bar (≥ 90).
"""

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class EvalResult:
    coverage_pct: float = 0.0
    data_completeness_pct: float = 0.0
    financial_coverage_pct: float = 0.0
    price_coverage_pct: float = 0.0
    error_rate_pct: float = 0.0
    score: float = 0.0
    details: dict = field(default_factory=dict)


class SelfEvaluator:
    """Score a crawl run against the v2 quality rubric."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def evaluate(self) -> EvalResult:
        """Run evaluation queries and compute the score."""
        result = EvalResult()
        if self._session_factory is None:
            return result

        try:
            from sqlalchemy import text

            with self._session_factory() as session:
                total = session.execute(
                    text("SELECT COUNT(*) FROM companies")
                ).scalar() or 0

                if total == 0:
                    return result

                crawled = session.execute(
                    text(
                        "SELECT COUNT(DISTINCT ticker) "
                        "FROM crawl_log WHERE status = 'success'"
                    )
                ).scalar() or 0

                with_financials = session.execute(
                    text(
                        "SELECT COUNT(DISTINCT company_id) FROM financials"
                    )
                ).scalar() or 0

                with_prices = session.execute(
                    text(
                        "SELECT COUNT(DISTINCT company_id) FROM stock_prices"
                    )
                ).scalar() or 0

                errors = session.execute(
                    text(
                        "SELECT COUNT(*) FROM crawl_log "
                        "WHERE status = 'failed'"
                    )
                ).scalar() or 0
                total_logs = session.execute(
                    text("SELECT COUNT(*) FROM crawl_log")
                ).scalar() or 1

                result.coverage_pct = (crawled / total) * 100
                result.financial_coverage_pct = (with_financials / total) * 100
                result.price_coverage_pct = (with_prices / total) * 100
                result.error_rate_pct = (errors / total_logs) * 100

                # Data completeness: % of non-NULL priority fields
                non_null = session.execute(
                    text("""
                        SELECT
                          (SUM(price_to_earnings IS NOT NULL)
                           + SUM(roe IS NOT NULL)
                           + SUM(eps IS NOT NULL))
                          / (COUNT(*) * 3) * 100
                        FROM financials
                    """)
                ).scalar() or 0
                result.data_completeness_pct = float(non_null)

        except Exception as exc:
            logger.error(f"Self-evaluation query failed: {exc}")

        result.score = self._compute_score(result)
        return result

    @staticmethod
    def _compute_score(r: EvalResult) -> float:
        """Weighted score (100-point scale).

        - Coverage > 90%: 25 pts
        - Data completeness > 80%: 25 pts
        - Financial coverage > 90%: 20 pts
        - Price coverage > 95%: 15 pts
        - Error rate < 5%: 15 pts
        """
        score = 0.0
        score += min(r.coverage_pct / 90 * 25, 25)
        score += min(r.data_completeness_pct / 80 * 25, 25)
        score += min(r.financial_coverage_pct / 90 * 20, 20)
        score += min(r.price_coverage_pct / 95 * 15, 15)
        if r.error_rate_pct < 5:
            score += 15
        elif r.error_rate_pct < 10:
            score += 10
        elif r.error_rate_pct < 20:
            score += 5
        return round(score, 1)
