# Speech-to-Text CLI

A powerful command-line interface for speech-to-text transcription using Google Vertex AI, with built-in support for speaker diarization and automatic language detection.

## Features

- **Speaker Diarization**: Automatically identify and label different speakers in audio recordings
- **Automatic Language Detection**: Support for mixed-language conversations (Hebrew and English by default)
- **Multiple Audio Formats**: Support for WAV, MP3, FLAC, OGG, WebM, AMR, and AMR-WB files
- **Flexible Output Formats**: Text, JSON, and detailed formats available
- **Easy Installation**: Install via pipx for global CLI access

## Installation

### Using pipx (Recommended)

```bash
pipx install stt-cli
```

### Using pip

```bash
pip install stt-cli
```

### From Source

```bash
git clone <repository-url>
cd stt-cli
uv install -e .
```

## Prerequisites

### Google Cloud Setup

1. **Create a Google Cloud Project** and enable the Speech-to-Text API
2. **Set up authentication** using one of these methods:

   **Option 1: Service Account (Recommended)**
   - Create a service account in the Google Cloud Console
   - Download the JSON key file
   - Use the `--google-credentials` flag to specify the path

   **Option 2: Application Default Credentials**
   - Install and initialize the Google Cloud CLI: `gcloud auth application-default login`
   - The CLI will automatically use these credentials

## Usage

### Basic Usage

```bash
# Transcribe an audio file with default settings
stt-cli transcribe audio.wav

# Specify custom speaker range
stt-cli transcribe --min-speakers 2 --max-speakers 4 audio.wav

# Use specific languages for detection
stt-cli transcribe --languages iw-IL --languages en-US audio.wav

# Output in JSON format
stt-cli transcribe --output-format json audio.wav

# Save output to file
stt-cli transcribe --output-file transcript.txt audio.wav
```

### Advanced Usage

```bash
# Detailed output with confidence scores
stt-cli transcribe --output-format detailed audio.wav

# Use service account credentials
stt-cli transcribe --google-credentials /path/to/credentials.json audio.wav

# Process with specific speaker count and languages
stt-cli transcribe \
  --min-speakers 1 \
  --max-speakers 3 \
  --languages iw-IL \
  --languages en-US \
  --output-format json \
  --output-file results.json \
  audio.wav
```

## Command Reference

### `stt-cli transcribe`

Transcribe audio file with speaker diarization and language detection.

**Arguments:**
- `AUDIO_FILE`: Path to the audio file to transcribe

**Options:**
- `--min-speakers INTEGER`: Minimum number of speakers (1-10, default: 1)
- `--max-speakers INTEGER`: Maximum number of speakers (1-10, default: 6)
- `--languages TEXT`: Languages to detect (up to 3). Use language codes like 'iw-IL', 'en-US'
- `--output-format [text|json|detailed]`: Output format (default: text)
- `--output-file PATH`: Output file path (default: stdout)
- `--google-credentials PATH`: Path to Google Cloud service account JSON file
- `--gcs-bucket TEXT`: Google Cloud Storage bucket name for large files (default: PROJECT_ID-stt-cli-audio)

## Supported Audio Formats

- **WAV** (.wav) - Linear PCM
- **FLAC** (.flac) - Free Lossless Audio Codec
- **MP3** (.mp3) - MPEG Audio Layer III
- **OGG** (.ogg) - Ogg Opus
- **WebM** (.webm) - WebM Opus
- **AMR** (.amr) - Adaptive Multi-Rate
- **AMR-WB** (.awb) - Adaptive Multi-Rate Wideband

## Output Formats

### Text Format (Default)
```
[Speaker 1]
Hello, how are you today?

[Speaker 2]
I'm doing well, thank you for asking.
```

### JSON Format
```json
{
  "transcription": {
    "segments": [
      {
        "id": 1,
        "transcript": "Hello, how are you today?",
        "confidence": 0.95,
        "speaker_tag": 1,
        "language_code": "en-US"
      }
    ],
    "summary": {
      "total_segments": 1,
      "speakers": 2,
      "languages": ["en-US", "he-IL"]
    }
  }
}
```

### Detailed Format
```
=== TRANSCRIPTION SUMMARY ===
Total segments: 2
Speakers detected: 2
Languages detected: en-US, he-IL

=== DETAILED TRANSCRIPTION ===

Segment 1:
  Speaker: Speaker 1
  Language: en-US
  Confidence: 95%
  Transcript: Hello, how are you today?
```

## Language Support

The CLI supports automatic detection of multiple languages. Default languages are Hebrew (iw-IL) and English (en-US), but you can specify up to 3 different languages:

```bash
# Detect Hebrew and English (default)
stt-cli transcribe audio.wav

# Detect Hebrew, English, and Spanish
stt-cli transcribe --languages iw-IL --languages en-US --languages es-ES audio.wav
```

Common language codes:
- `iw-IL` - Hebrew (Israel)
- `en-US` - English (US)
- `es-ES` - Spanish (Spain)
- `fr-FR` - French (France)
- `de-DE` - German (Germany)

## Environment Variables

- `STT_CLI_GCS_BUCKET`: Set the Google Cloud Storage bucket name for large file uploads
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud service account JSON file

## Large File Handling

For audio files larger than 10MB, the CLI automatically uploads them to Google Cloud Storage before processing. By default, it creates a bucket named `{PROJECT_ID}-stt-cli-audio`. You can customize this by:

1. Using the `--gcs-bucket` option
2. Setting the `STT_CLI_GCS_BUCKET` environment variable

The bucket will be created automatically if it doesn't exist (requires appropriate GCS permissions).

## Development

### Setup Development Environment

```bash
git clone <repository-url>
cd stt-cli
uv sync --dev
```

### Run Tests

```bash
uv run pytest
```

### Code Formatting and Linting

```bash
uv run ruff check --fix
uv run ruff format
```

## Limitations

- Maximum file size depends on Google Cloud Speech-to-Text API limits
- Requires Google Cloud credentials and active billing account
- Speaker diarization works best with clear audio and distinct speakers
- Language detection is limited to 3 languages per request
- **Speaker diarization is not supported for Hebrew (iw-IL)** - this is a limitation of the Google Cloud Speech-to-Text API

## Support

For issues and feature requests, please visit the project repository.

## License

This project is licensed under the MIT License.