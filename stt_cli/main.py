"""Main CLI module for speech-to-text transcription."""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import click

from .audio_processor import AudioProcessor
from .output_formatter import OutputFormatter
from .speech_client import SpeechClient


def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


class DefaultGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        # Only return the command if it exists
        return click.Group.get_command(self, ctx, cmd_name)
    def parse_args(self, ctx, args):
        # If the first argument is not a command, insert the default command
        if args and not self.get_command(ctx, args[0]):
            args.insert(0, 'transcribe')
        super().parse_args(ctx, args)


@click.group(cls=DefaultGroup)
@click.version_option()
def cli():
    """Speech-to-text CLI with AWS Transcribe.

    Supports speaker diarization and automatic language detection.
    
    If no command is specified, 'transcribe' is used by default.
    """
    pass


@cli.command()
@click.argument("audio_file", required=False, type=click.Path(exists=True, path_type=Path))
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
    "--timeout",
    type=int,
    default=3600,
    envvar="STT_CLI_TIMEOUT",
    help="Timeout in seconds for transcription job (default: 3600). "
    "Can also be set via STT_CLI_TIMEOUT environment variable.",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
def transcribe(
    audio_file: Optional[Path] = None,
    min_speakers: int = 1,
    max_speakers: int = 6,
    languages: tuple[str, ...] = (),
    output_format: str = "text",
    output_file: Optional[Path] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region: str = "us-east-1",
    s3_bucket: Optional[str] = None,
    timeout: int = 3600,
    debug: bool = False,
):
    """Transcribe audio file with speaker diarization and language detection."""
    if audio_file is None:
        click.echo("Error: Missing required argument 'AUDIO_FILE'", err=True)
        click.echo(transcribe.get_help(click.Context(transcribe)))
        sys.exit(2)

    # Configure logging if debug is enabled
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.getLogger('stt_cli').setLevel(logging.DEBUG)
    else:
        # Set up basic info logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )
        logging.getLogger('stt_cli').setLevel(logging.INFO)
    
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
        logging.info(f"Processing audio file: {audio_file}")
        audio_config = audio_processor.process_file(audio_file)

        # Check file size and inform user
        file_size_mb = len(audio_config.content) / (1024 * 1024) if audio_config.content else 0
        logging.info(f"File size: {file_size_mb:.1f} MB")
        
        logging.info("Uploading to S3 and starting transcription job...")
        logging.info("This may take several minutes depending on file size...")
            
        start_time = time.time()
        result = speech_client.transcribe(
            audio_config=audio_config,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            languages=list(languages),
            timeout=timeout,
        )
        end_time = time.time()
        duration = round(end_time - start_time, 2)

        logging.info("Transcription completed successfully")

        # Format output
        output = formatter.format_result(result, output_format)

        # Write output
        if output_file:
            output_file.write_text(output, encoding="utf-8")
            click.echo(f"Results written to: {output_file}")
        else:
            click.echo(output)

        logging.info(f"Transcription took {format_duration(duration)}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
