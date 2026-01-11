"""Test CLI functionality."""

import pytest
from click.testing import CliRunner

from stt_cli.main import cli


def test_cli_help():
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # DefaultGroup redirects to transcribe command help
    assert "Transcribe audio file with speaker diarization" in result.output


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

    # Test with min_speakers > 30 (AWS limit)
    result = runner.invoke(cli, ["transcribe", "--min-speakers", "35", "test.wav"])
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
        "--languages", "fr-FR",
        "--languages", "de-DE",  # 5th language should trigger the error
        "test.wav"
    ])
    assert result.exit_code != 0


def test_transcribe_help_shows_timeout_option():
    """Test that transcribe command help shows timeout option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "--timeout" in result.output
    assert "3600" in result.output  # default value


def test_transcribe_timeout_option_accepted():
    """Test that timeout option is accepted (doesn't error on missing file)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["transcribe", "--timeout", "7200", "test.wav"])
    # Should fail because file doesn't exist, not because of invalid option
    assert "does not exist" in result.output.lower()