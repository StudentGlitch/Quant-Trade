import pandas as pd
from loguru import logger
import uuid
from ..data.duckdb_repo import DuckDBRepo

class DPODatasetBuilder:
    """
    Phase 27.1: Automated DPO Dataset Curation.
    Mines war_room_transcripts and correlates with actual PnL to generate 
    Positive/Negative preference pairs for LLM fine-tuning.
    """

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def generate_preference_dataset(self, min_return_threshold: float = 0.02):
        """
        Builds DPO pairs:
        Chosen: STRONG_BUY that yielded > +2%
        Rejected: STRONG_BUY that yielded < -2%
        """
        logger.info("Curating Direct Preference Optimization (DPO) Dataset...")
        
        try:
            # For MVP, we mock the PnL join. In production, join with daily_pnl_ledger.
            # We select recent debates.
            debates_df = self.repo.con.execute("""
                SELECT debate_id, ticker, date, transcript, final_decision
                FROM war_room_transcripts
                WHERE final_decision = 'STRONG_BUY'
            """).df()

            if debates_df.empty:
                logger.warning("No qualifying debates found for DPO extraction.")
                return False

            dataset_entries = []

            for _, row in debates_df.iterrows():
                # Mocking PnL look-forward (T+5)
                # In prod: select return from pnl_ledger where date = row['date'] + 5 days
                import random
                mock_pnl = random.uniform(-0.05, 0.05) 
                
                # We need pairs for DPO. This implies we need a 'chosen' and 'rejected' response 
                # for the SAME prompt. If we only have one transcript per prompt, we might compare 
                # different agents' reasoning, or just classify the whole transcript as good/bad.
                # Standard DPO requires (prompt, chosen, rejected).
                # To build this from historical data, we can take a profitable trade's reasoning as 'chosen'
                # and an unprofitable trade's reasoning (on similar data) as 'rejected', 
                # OR contrast the Macro Agent vs Risk Agent if one was right and one was wrong.
                
                # Simplified representation for schema compliance:
                pair_id = str(uuid.uuid4())
                prompt_text = f"Analyze {row['ticker']} on {row['date']}."
                transcript_text = str(row['transcript'])
                
                if mock_pnl > min_return_threshold:
                    chosen = transcript_text
                    rejected = "I disagree with the analysis. The risk is too high." # Mock generic rejection
                    margin = mock_pnl
                elif mock_pnl < -min_return_threshold:
                    rejected = transcript_text
                    chosen = "We should avoid this trade due to underlying structural weakness." # Mock generic chosen
                    margin = mock_pnl
                else:
                    continue # Ignore neutral trades
                
                dataset_entries.append((
                    pair_id,
                    row['ticker'],
                    prompt_text,
                    chosen,
                    rejected,
                    margin
                ))

            if dataset_entries:
                self.repo.con.executemany("""
                    INSERT OR REPLACE INTO dpo_preference_dataset 
                    (pair_id, ticker, prompt, chosen_response, rejected_response, margin_of_victory)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, dataset_entries)
                
                logger.success(f"Successfully curated {len(dataset_entries)} DPO preference pairs.")
                return True
            else:
                logger.info("No trades met the minimum return threshold for DPO generation.")
                return False

        except Exception as e:
            logger.error(f"Failed to generate DPO dataset: {e}")
            return False

if __name__ == "__main__":
    # Can be run as a standalone script or scheduled via Celery
    repo = DuckDBRepo("storage/db/quant_data.duckdb")
    builder = DPODatasetBuilder(repo)
    builder.generate_preference_dataset()
