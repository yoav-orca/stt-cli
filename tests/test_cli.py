"""Test CLI functionality."""

import pytest
from click.testing import CliRunner

from stt_cli.main import cli


def test_cli_help():
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Speech-to-text CLI with Google Vertex AI" in result.output


def test_transcribe_help():
    """Test that transcribe command help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "Transcribe audio file with speaker diarization" in result.output


def test_transcribe_missing_file():
    """Test transcribe command with missing audio file."""
    runner = CliRunner()
    result = runner.invoke(cli, ["transcribe", "nonexistent.wav"])
    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_transcribe_invalid_speakers():
    """Test transcribe command with invalid speaker counts."""
    runner = CliRunner()
    
    # Test with min_speakers > 10
    result = runner.invoke(cli, ["transcribe", "--min-speakers", "15", "test.wav"])
    assert result.exit_code != 0
    
    # Test with max_speakers < 1
    result = runner.invoke(cli, ["transcribe", "--max-speakers", "0", "test.wav"])
    assert result.exit_code != 0


def test_transcribe_too_many_languages():
    """Test transcribe command with too many languages."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "transcribe", 
        "--languages", "en-US", 
        "--languages", "he-IL", 
        "--languages", "es-ES", 
        "--languages", "fr-FR",  # This should trigger the error
        "test.wav"
    ])
    assert result.exit_code != 0