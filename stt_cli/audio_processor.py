"""Audio file processing and validation."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .speech_client import AudioConfig


class AudioProcessor:
    """Handles audio file processing and format detection."""

    # Supported audio formats for AWS Transcribe
    SUPPORTED_FORMATS = {
        '.wav': 'wav',
        '.mp3': 'mp3',
        '.mp4': 'mp4',
        '.m4a': 'mp4',  # M4A is container format, usually mp4
        '.flac': 'flac',
        '.ogg': 'ogg',
        '.amr': 'amr',
        '.webm': 'webm',
    }
    
    # Video formats that need ffmpeg conversion
    # Note: .mp4 and .webm can contain audio-only, so they're not included here
    VIDEO_FORMATS = {
        '.avi',
        '.mov',
        '.mkv',
        '.flv',
        '.wmv',
        '.mpg',
        '.mpeg',
        '.3gp',
        '.m4v',
    }

    def __init__(self):
        """Initialize the audio processor."""
        self.logger = logging.getLogger(__name__)

    def process_file(self, file_path: Path) -> AudioConfig:
        """Process an audio file and return AudioConfig.

        Args:
            file_path: Path to the audio file

        Returns:
            AudioConfig object with file content and detected format

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Check if it's a video file that needs conversion
        if self._is_video_format(file_path):
            self.logger.info(f"Detected video file {file_path.suffix}, converting to MP3...")
            file_path = self._convert_video_to_mp3(file_path)
            self.logger.info("Video conversion completed successfully")

        # Detect file format
        media_format = self._detect_format(file_path)
        if media_format is None:
            raise ValueError(f"Unsupported audio format: {file_path.suffix}")

        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()

        # For most formats, we'll use default settings
        # In a production system, you might want to analyze the audio
        # to determine sample rate and channel count
        sample_rate = self._detect_sample_rate(file_path, media_format)

        return AudioConfig(
            content=content,
            media_format=media_format,
            sample_rate=sample_rate,
        )

    def _detect_format(self, file_path: Path) -> Optional[str]:
        """Detect the audio format from file extension.

        Args:
            file_path: Path to the audio file

        Returns:
            AWS Transcribe media format string or None if unsupported
        """
        suffix = file_path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(suffix)

    def _detect_sample_rate(self, file_path: Path, media_format: str) -> Optional[int]:
        """Detect or estimate sample rate for the audio file.

        For now, returns common default values based on format.
        In a production system, you'd want to use a library like librosa
        or pydub to analyze the actual audio properties.

        Args:
            file_path: Path to the audio file
            media_format: Audio format

        Returns:
            Sample rate in Hz or None for auto-detection
        """
        # AWS Transcribe can auto-detect sample rate for most formats
        # We'll only specify it for formats that benefit from it
        if media_format in ['wav', 'flac']:
            # For WAV and FLAC, 16kHz is optimal for speech recognition
            return 16000
        elif media_format == 'amr':
            # AMR has fixed sample rates
            return 8000
        
        # Let AWS auto-detect for other formats
        return None

    def is_supported_format(self, file_path: Path) -> bool:
        """Check if the audio file format is supported.

        Args:
            file_path: Path to the audio file

        Returns:
            True if format is supported, False otherwise
        """
        suffix = file_path.suffix.lower()
        return suffix in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> list[str]:
        """Get list of supported audio file extensions.

        Returns:
            List of supported file extensions
        """
        return list(self.SUPPORTED_FORMATS.keys())

    def _is_video_format(self, file_path: Path) -> bool:
        """Check if the file is a video format that needs conversion.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is a video format, False otherwise
        """
        suffix = file_path.suffix.lower()
        return suffix in self.VIDEO_FORMATS

    def _convert_video_to_mp3(self, video_path: Path) -> Path:
        """Convert video file to MP3 using ffmpeg.

        Args:
            video_path: Path to the video file

        Returns:
            Path to the converted MP3 file

        Raises:
            RuntimeError: If ffmpeg conversion fails
        """
        # Create a temporary MP3 file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            mp3_path = Path(tmp_file.name)

        try:
            # Check if ffmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("ffmpeg is not installed or not available in PATH")

            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',  # No video
                '-acodec', 'mp3',
                '-ab', '192k',  # Audio bitrate
                '-ar', '16000',  # Sample rate optimized for speech
                '-ac', '1',  # Mono audio
                '-y',  # Overwrite output file
                str(mp3_path)
            ]

            self.logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")

            # Run ffmpeg conversion
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                error_msg = f"ffmpeg conversion failed: {result.stderr}"
                self.logger.error(error_msg)
                # Clean up temporary file on failure
                if mp3_path.exists():
                    mp3_path.unlink()
                raise RuntimeError(error_msg)

            return mp3_path

        except Exception as e:
            # Clean up temporary file on any error
            if mp3_path.exists():
                mp3_path.unlink()
            raise RuntimeError(f"Failed to convert video to MP3: {str(e)}")