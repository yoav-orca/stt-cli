"""Main CLI module for speech-to-text transcription."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click

from .audio_processor import AudioProcessor
from .output_formatter import OutputFormatter
from .speech_client import SpeechClient


@click.group()
@click.version_option()
def cli():
    """Speech-to-text CLI with Google Vertex AI.

    Supports speaker diarization and automatic language detection.
    """
    pass


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--min-speakers",
    type=int,
    default=1,
    help="Minimum number of speakers (1-10, default: 1)",
)
@click.option(
    "--max-speakers",
    type=int,
    default=6,
    help="Maximum number of speakers (1-10, default: 6)",
)
@click.option(
    "--languages",
    multiple=True,
    help="Languages to detect (up to 3). Use language codes like 'en-US', 'he-IL'. "
    "If not specified, defaults to 'en-US' and 'he-IL'.",
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json", "detailed"]),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--output-file",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)",
)
@click.option(
    "--google-credentials",
    type=click.Path(exists=True, path_type=Path),
    help="Path to Google Cloud service account JSON file",
)
@click.option(
    "--gcs-bucket",
    envvar="STT_CLI_GCS_BUCKET",
    help="Google Cloud Storage bucket name for large files. If not specified, uses PROJECT_ID-stt-cli-audio. "
    "Can also be set via STT_CLI_GCS_BUCKET environment variable.",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
def transcribe(
    audio_file: Path,
    min_speakers: int,
    max_speakers: int,
    languages: tuple[str, ...],
    output_format: str,
    output_file: Optional[Path],
    google_credentials: Optional[Path],
    gcs_bucket: Optional[str],
    debug: bool,
):
    """Transcribe audio file with speaker diarization and language detection."""
    # Configure logging if debug is enabled
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.getLogger('stt_cli').setLevel(logging.DEBUG)
    
    # Validate speaker count
    if min_speakers < 1 or min_speakers > 10:
        click.echo("Error: min-speakers must be between 1 and 10", err=True)
        sys.exit(1)

    if max_speakers < 1 or max_speakers > 10:
        click.echo("Error: max-speakers must be between 1 and 10", err=True)
        sys.exit(1)

    if min_speakers > max_speakers:
        click.echo("Error: min-speakers cannot be greater than max-speakers", err=True)
        sys.exit(1)

    # Validate languages
    if len(languages) > 3:
        click.echo("Error: Maximum 3 languages allowed", err=True)
        sys.exit(1)

    # Default languages if none specified (Hebrew first for better detection)
    if not languages:
        languages = ("iw-IL", "en-US")
    
    # Warn about speaker diarization limitations
    if languages[0] == "iw-IL" and (min_speakers > 1 or max_speakers > 1):
        click.echo("Warning: Speaker diarization is not supported for Hebrew (iw-IL) by Google Cloud Speech-to-Text.", err=True)
        click.echo("The transcription will proceed without speaker separation.", err=True)

    try:
        # Initialize components
        audio_processor = AudioProcessor()
        speech_client = SpeechClient(credentials_path=google_credentials, bucket_name=gcs_bucket)
        formatter = OutputFormatter()

        # Process audio file
        click.echo(f"Processing audio file: {audio_file}")
        audio_config = audio_processor.process_file(audio_file)

        # Check file size and inform user
        file_size_mb = len(audio_config.content) / (1024 * 1024)
        click.echo(f"File size: {file_size_mb:.1f} MB")
        
        if file_size_mb > 10:
            click.echo("Large file detected - uploading to Google Cloud Storage...")
            click.echo("Using long-running recognition (this may take several minutes)...")
        else:
            click.echo("Transcribing...")
            
        result = speech_client.transcribe(
            audio_config=audio_config,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            languages=list(languages),
        )

        # Format output
        output = formatter.format_result(result, output_format)

        # Write output
        if output_file:
            output_file.write_text(output, encoding="utf-8")
            click.echo(f"Results written to: {output_file}")
        else:
            click.echo(output)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
