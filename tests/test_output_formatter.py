"""Test output formatter functionality."""

import json
import pytest

from stt_cli.output_formatter import OutputFormatter
from stt_cli.speech_client import TranscriptionResult


class TestOutputFormatter:
    """Test cases for OutputFormatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = OutputFormatter()
        self.sample_results = [
            TranscriptionResult("Hello world", 0.95, "en-US", 1),
            TranscriptionResult("שלום עולם", 0.88, "he-IL", 2),
            TranscriptionResult("How are you?", 0.92, "en-US", 1),
        ]
    
    def test_format_empty_results(self):
        """Test formatting empty results."""
        output = self.formatter.format_result([], "text")
        assert output == "No transcription results found."
    
    def test_format_text(self):
        """Test text formatting."""
        output = self.formatter.format_result(self.sample_results, "text")
        
        assert "[Speaker 1]" in output
        assert "[Speaker 2]" in output
        assert "Hello world" in output
        assert "שלום עולם" in output
        assert "How are you?" in output
    
    def test_format_json(self):
        """Test JSON formatting."""
        output = self.formatter.format_result(self.sample_results, "json")
        data = json.loads(output)
        
        assert "transcription" in data
        assert "segments" in data["transcription"]
        assert "summary" in data["transcription"]
        
        summary = data["transcription"]["summary"]
        assert summary["total_segments"] == 3
        assert summary["speakers"] == 2
        assert "en-US" in summary["languages"]
        assert "he-IL" in summary["languages"]
        
        segments = data["transcription"]["segments"]
        assert len(segments) == 3
        assert segments[0]["transcript"] == "Hello world"
        assert segments[0]["speaker_tag"] == 1
    
    def test_format_detailed(self):
        """Test detailed formatting."""
        output = self.formatter.format_result(self.sample_results, "detailed")
        
        assert "=== TRANSCRIPTION SUMMARY ===" in output
        assert "Total segments: 3" in output
        assert "Speakers detected: 2" in output
        assert "Languages detected: en-US, he-IL" in output
        
        assert "=== DETAILED TRANSCRIPTION ===" in output
        assert "Segment 1:" in output
        assert "Speaker: Speaker 1" in output
        assert "Confidence: 95%" in output
    
    def test_unsupported_format(self):
        """Test unsupported format type."""
        with pytest.raises(ValueError, match="Unsupported format type"):
            self.formatter.format_result(self.sample_results, "invalid")
    
    def test_unknown_speaker(self):
        """Test formatting with unknown speaker."""
        results = [TranscriptionResult("Test", 0.9, "en-US", None)]
        output = self.formatter.format_result(results, "text")
        assert "[Unknown Speaker]" in output
    
    def test_group_by_speaker(self):
        """Test speaker grouping functionality."""
        groups = self.formatter._group_by_speaker(self.sample_results)
        
        assert 1 in groups
        assert 2 in groups
        assert len(groups[1]) == 2  # Two segments from speaker 1
        assert len(groups[2]) == 1  # One segment from speaker 2