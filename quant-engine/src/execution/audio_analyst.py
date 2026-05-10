import os
import whisper
import librosa
import numpy as np
from loguru import logger
from datetime import datetime
from typing import List, Dict
from src.data.duckdb_repo import DuckDBRepo

class AudioAnalyst:
    """ASR transcription and Vocal Stress Analysis using Whisper and Librosa."""

    def __init__(self, repo: DuckDBRepo, model_name: str = "base"):
        self.repo = repo
        logger.info(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)
        self.fillers = ["um", "uh", "ah", "er", "hm", "like", "you know"]

    def analyze_corporate_call(self, ticker: str, audio_path: str, event_type: str = "EARNINGS_CALL"):
        """Perform full transcription and hesitation analysis."""
        logger.info(f"Analyzing audio for {ticker}: {audio_path}")
        
        # 1. Transcribe with timestamps
        result = self.model.transcribe(audio_path, verbose=False)
        transcript = result["text"]
        segments = result["segments"]

        # 2. Calculate Vocal Hesitation Index (VHI)
        vhi, n_fillers, n_pauses = self._calculate_vhi(segments)
        
        # 3. Basic Sentiment (Mock/Placeholder for V1 or use simple keyword logic)
        sentiment_score = 0.5  # Neutral default

        media_id = os.path.basename(audio_path).split('.')[0]
        
        # 4. Store in DuckDB
        self.repo.con.execute("""
            INSERT OR REPLACE INTO audio_perception_ledger 
            (media_id, ticker, date, event_type, transcript, hesitation_index, audio_sentiment_score, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [media_id, ticker, datetime.now().date(), event_type, transcript, vhi, sentiment_score, datetime.now()])

        logger.success(f"Perception Complete: {ticker} VHI={vhi:.2f} (Stress: {'HIGH' if vhi > 5.0 else 'LOW'})")
        return {
            "media_id": media_id,
            "vhi": vhi,
            "transcript": transcript,
            "is_high_stress": vhi > 5.0
        }

    def _calculate_vhi(self, segments: List[Dict]) -> (float, int, int):
        """
        VHI = (N_fillers + (N_pauses * 1.5)) / N_total * 100
        N_pauses: gaps > 2.0 seconds
        """
        n_total_words = 0
        n_fillers = 0
        n_pauses = 0
        
        last_end_time = 0.0
        
        for seg in segments:
            text = seg["text"].lower()
            words = text.split()
            n_total_words += len(words)
            
            # Count fillers
            for filler in self.fillers:
                n_fillers += text.count(filler)
            
            # Detect silence gaps between segments
            gap = seg["start"] - last_end_time
            if gap > 2.0:
                n_pauses += 1
            last_end_time = seg["end"]

        if n_total_words == 0:
            return 0.0, 0, 0

        vhi = ((n_fillers + (n_pauses * 1.5)) / n_total_words) * 100
        return vhi, n_fillers, n_pauses
