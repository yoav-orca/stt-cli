"""Test audio processor functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from stt_cli.audio_processor import AudioProcessor
from google.cloud import speech_v1p1beta1 as speech


class TestAudioProcessor:
    """Test cases for AudioProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = AudioProcessor()
    
    def test_supported_formats(self):
        """Test that supported formats are correctly identified."""
        supported = self.processor.get_supported_formats()
        expected = ['.wav', '.flac', '.mp3', '.ogg', '.webm', '.amr', '.awb']
        assert all(fmt in supported for fmt in expected)
    
    def test_is_supported_format(self):
        """Test format detection."""
        assert self.processor.is_supported_format(Path("test.wav"))
        assert self.processor.is_supported_format(Path("test.mp3"))
        assert not self.processor.is_supported_format(Path("test.txt"))
        assert not self.processor.is_supported_format(Path("test.xyz"))
    
    def test_detect_encoding(self):
        """Test encoding detection from file extension."""
        # Test WAV files
        encoding = self.processor._detect_encoding(Path("test.wav"))
        assert encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
        
        # Test MP3 files
        encoding = self.processor._detect_encoding(Path("test.mp3"))
        assert encoding == speech.RecognitionConfig.AudioEncoding.MP3
        
        # Test unsupported format
        encoding = self.processor._detect_encoding(Path("test.txt"))
        assert encoding is None
    
    def test_detect_sample_rate(self):
        """Test sample rate detection."""
        # Test WAV/LINEAR16
        rate = self.processor._detect_sample_rate(
            Path("test.wav"), 
            speech.RecognitionConfig.AudioEncoding.LINEAR16
        )
        assert rate == 16000
        
        # Test MP3
        rate = self.processor._detect_sample_rate(
            Path("test.mp3"), 
            speech.RecognitionConfig.AudioEncoding.MP3
        )
        assert rate == 44100
    
    def test_detect_channels(self):
        """Test channel detection."""
        channels = self.processor._detect_channels(Path("test.wav"))
        assert channels == 1  # Should always return mono for speech
    
    @patch("pathlib.Path.exists")
    def test_process_file_not_exists(self, mock_exists):
        """Test processing non-existent file."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            self.processor.process_file(Path("nonexistent.wav"))
    
    @patch("pathlib.Path.exists")
    def test_process_file_unsupported_format(self, mock_exists):
        """Test processing unsupported file format."""
        mock_exists.return_value = True
        
        with pytest.raises(ValueError, match="Unsupported audio format"):
            self.processor.process_file(Path("test.txt"))
    
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake audio data")
    def test_process_file_success(self, mock_file, mock_exists):
        """Test successful file processing."""
        mock_exists.return_value = True
        
        config = self.processor.process_file(Path("test.wav"))
        
        assert config.content == b"fake audio data"
        assert config.encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
        assert config.sample_rate_hertz == 16000
        assert config.audio_channel_count == 1