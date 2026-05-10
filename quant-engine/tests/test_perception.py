import pytest
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before importing AudioAnalyst
mock_whisper = MagicMock()
sys.modules["whisper"] = mock_whisper
mock_librosa = MagicMock()
sys.modules["librosa"] = mock_librosa

from src.execution.audio_analyst import AudioAnalyst

def test_vhi_calculation():
    # Mock repo
    mock_repo = MagicMock()
    # Ensure load_model doesn't actually try to load anything
    mock_whisper.load_model.return_value = MagicMock()
    
    analyst = AudioAnalyst(repo=mock_repo)
    
    # Mock segments for 100 words, 5 fillers, and 2 gaps > 2s
    long_text = "word " * 85
    segments = [
        {"text": "um um um um um " + long_text, "start": 0.0, "end": 50.0}, # 5 fillers, 90 words
        {"text": "word word word word word", "start": 53.0, "end": 55.0}, # 5 words. Gap = 3.0 -> 1 pause
        {"text": "word word word word word", "start": 58.0, "end": 60.0}  # 5 words. Gap = 3.0 -> 1 pause
    ]
    
    vhi, n_fillers, n_pauses = analyst._calculate_vhi(segments)
    
    assert n_fillers == 5
    assert n_pauses == 2
    assert vhi == 8.0

