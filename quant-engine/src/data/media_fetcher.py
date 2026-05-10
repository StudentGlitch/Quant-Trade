import os
import subprocess
from pathlib import Path
from loguru import logger

class MediaFetcher:
    """Utility to extract audio from YouTube or corporate webcasts using yt-dlp."""

    def __init__(self, temp_dir: str = "src/temp_media"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def fetch_audio(self, url: str, media_id: str) -> str:
        """
        Download only the audio track from a URL.
        Returns the local path to the downloaded audio file.
        """
        output_template = str(self.temp_dir / f"{media_id}.%(ext)s")
        logger.info(f"Fetching audio from {url}...")

        try:
            # yt-dlp command to extract best audio only
            command = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", "m4a",
                "-o", output_template,
                url
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            # Find the actual file (ext might vary if bestaudio is used, but we forced m4a)
            audio_path = self.temp_dir / f"{media_id}.m4a"
            if audio_path.exists():
                logger.success(f"Audio downloaded: {audio_path}")
                return str(audio_path)
            else:
                raise FileNotFoundError(f"Expected audio file {audio_path} not found.")

        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp failed for {url}: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching audio: {e}")
            raise

    def cleanup(self, file_path: str):
        """Delete temporary media file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")
