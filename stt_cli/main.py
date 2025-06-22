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
    """Speech-to-text CLI with AWS Transcribe.

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
    help="Maximum number of speakers (1-30, default: 6)",
)
@click.option(
    "--languages",
    multiple=True,
    help="Languages to detect (up to 4). Use language codes like 'en-US', 'he-IL'. "
    "If not specified, defaults to 'he-IL' and 'en-US'.",
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
    "--aws-access-key-id",
    envvar="AWS_ACCESS_KEY_ID",
    help="AWS access key ID. Can also be set via AWS_ACCESS_KEY_ID environment variable.",
)
@click.option(
    "--aws-secret-access-key",
    envvar="AWS_SECRET_ACCESS_KEY",
    help="AWS secret access key. Can also be set via AWS_SECRET_ACCESS_KEY environment variable.",
)
@click.option(
    "--aws-region",
    default="us-east-1",
    envvar="AWS_DEFAULT_REGION",
    help="AWS region (default: us-east-1). Can also be set via AWS_DEFAULT_REGION environment variable.",
)
@click.option(
    "--s3-bucket",
    envvar="STT_CLI_S3_BUCKET",
    help="S3 bucket name for audio uploads. If not specified, creates a temporary bucket. "
    "Can also be set via STT_CLI_S3_BUCKET environment variable.",
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
    aws_access_key_id: Optional[str],
    aws_secret_access_key: Optional[str],
    aws_region: str,
    s3_bucket: Optional[str],
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
    
    # Validate speaker count (AWS supports up to 30 speakers)
    if min_speakers < 1 or min_speakers > 30:
        click.echo("Error: min-speakers must be between 1 and 30", err=True)
        sys.exit(1)

    if max_speakers < 1 or max_speakers > 30:
        click.echo("Error: max-speakers must be between 1 and 30", err=True)
        sys.exit(1)

    if min_speakers > max_speakers:
        click.echo("Error: min-speakers cannot be greater than max-speakers", err=True)
        sys.exit(1)

    # Validate languages (AWS supports up to 4 languages for identification)
    if len(languages) > 4:
        click.echo("Error: Maximum 4 languages allowed", err=True)
        sys.exit(1)

    # Default languages if none specified (Hebrew first for better detection)
    if not languages:
        languages = ("he-IL", "en-US")  # AWS uses he-IL for Hebrew

    try:
        # Initialize components
        audio_processor = AudioProcessor()
        speech_client = SpeechClient(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            bucket_name=s3_bucket
        )
        formatter = OutputFormatter()

        # Process audio file
        click.echo(f"Processing audio file: {audio_file}")
        audio_config = audio_processor.process_file(audio_file)

        # Check file size and inform user
        file_size_mb = len(audio_config.content) if audio_config.content else 0 / (1024 * 1024)
        click.echo(f"File size: {file_size_mb:.1f} MB")
        
        click.echo("Uploading to S3 and starting transcription job...")
        click.echo("This may take several minutes depending on file size...")
            
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
