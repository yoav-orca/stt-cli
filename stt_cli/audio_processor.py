"""Audio file processing and validation."""

from pathlib import Path
from typing import Optional

from google.cloud import speech_v1p1beta1 as speech

from .speech_client import AudioConfig


class AudioProcessor:
    """Handles audio file processing and format detection."""

    # Supported audio formats and their Speech API encodings
    SUPPORTED_FORMATS = {
        '.wav': speech.RecognitionConfig.AudioEncoding.LINEAR16,
        '.flac': speech.RecognitionConfig.AudioEncoding.FLAC,
        '.mp3': speech.RecognitionConfig.AudioEncoding.MP3,
        '.m4a': speech.RecognitionConfig.AudioEncoding.MP3,  # M4A uses AAC, treat as MP3
        '.ogg': speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        '.webm': speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        '.amr': speech.RecognitionConfig.AudioEncoding.AMR,
        '.awb': speech.RecognitionConfig.AudioEncoding.AMR_WB,
    }

    def __init__(self):
        """Initialize the audio processor."""
        pass

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

        # Detect file format
        encoding = self._detect_encoding(file_path)
        if encoding is None:
            raise ValueError(f"Unsupported audio format: {file_path.suffix}")

        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()

        # For most formats, we'll use default settings
        # In a production system, you might want to analyze the audio
        # to determine sample rate and channel count
        sample_rate = self._detect_sample_rate(file_path, encoding)
        channels = self._detect_channels(file_path)

        return AudioConfig(
            content=content,
            encoding=encoding,
            sample_rate_hertz=sample_rate,
            audio_channel_count=channels,
        )

    def _detect_encoding(self, file_path: Path) -> Optional[speech.RecognitionConfig.AudioEncoding]:
        """Detect the audio encoding from file extension.

        Args:
            file_path: Path to the audio file

        Returns:
            Speech API encoding enum or None if unsupported
        """
        suffix = file_path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(suffix)

    def _detect_sample_rate(self, file_path: Path, encoding: speech.RecognitionConfig.AudioEncoding) -> int:
        """Detect or estimate sample rate for the audio file.

        For now, returns common default values based on format.
        In a production system, you'd want to use a library like librosa
        or pydub to analyze the actual audio properties.

        Args:
            file_path: Path to the audio file
            encoding: Audio encoding format

        Returns:
            Sample rate in Hz
        """
        # Default sample rates for different formats
        if encoding in [
            speech.RecognitionConfig.AudioEncoding.LINEAR16,
            speech.RecognitionConfig.AudioEncoding.FLAC,
        ]:
            # For WAV and FLAC, common rates are 16kHz, 44.1kHz, 48kHz
            # We'll default to 16kHz which is optimal for speech recognition
            return 16000
        elif encoding == speech.RecognitionConfig.AudioEncoding.MP3:
            # MP3 and M4A files often use 44.1kHz, but 16kHz works better for speech recognition
            return 16000
        elif encoding in [
            speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        ]:
            # Opus typically uses 48kHz
            return 48000
        elif encoding in [
            speech.RecognitionConfig.AudioEncoding.AMR,
            speech.RecognitionConfig.AudioEncoding.AMR_WB,
        ]:
            # AMR has fixed sample rates
            if encoding == speech.RecognitionConfig.AudioEncoding.AMR:
                return 8000
            else:  # AMR_WB
                return 16000

        # Default fallback
        return 16000

    def _detect_channels(self, file_path: Path) -> int:
        """Detect number of audio channels.

        For now, assumes mono audio which is typical for speech.
        In a production system, you'd analyze the actual file.

        Args:
            file_path: Path to the audio file

        Returns:
            Number of audio channels
        """
        # Most speech recordings are mono
        # The Speech API works better with mono audio for diarization
        return 1

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
