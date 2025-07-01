# Speech-to-Text CLI

A powerful command-line interface for speech-to-text transcription using AWS Transcribe, with built-in support for speaker diarization and automatic language detection.

## Features

- **Speaker Diarization**: Automatically identify and label different speakers in audio recordings (up to 30 speakers)
- **Automatic Language Detection**: Support for mixed-language conversations (Hebrew and English by default)
- **Multiple Audio/Video Formats**: Support for WAV, MP3, MP4, M4A, FLAC, OGG, AMR, WebM, and video formats (AVI, MOV, MKV, FLV, WMV, MPG, MPEG, 3GP, M4V) with automatic conversion
- **Flexible Output Formats**: Text, JSON, and detailed formats available
- **Easy Installation**: Install via pipx for global CLI access
- **Hebrew Support**: Full speaker diarization support for Hebrew language

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

### ffmpeg (Required for video files)

If you plan to transcribe video files, you'll need ffmpeg installed:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

### AWS Setup

1. **Create an AWS Account** and ensure you have access to Amazon Transcribe
2. **Set up authentication** using one of these methods:

   **Option 1: Environment Variables (Recommended)**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key_id
   export AWS_SECRET_ACCESS_KEY=your_secret_access_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

   **Option 2: AWS CLI Configuration**
   ```bash
   aws configure
   ```

   **Option 3: CLI Options**
   Use the `--aws-access-key-id`, `--aws-secret-access-key`, and `--aws-region` options

3. **Required AWS Permissions**:
   - `transcribe:StartTranscriptionJob`
   - `transcribe:GetTranscriptionJob`
   - `transcribe:DeleteTranscriptionJob`
   - `s3:CreateBucket`
   - `s3:PutObject`
   - `s3:DeleteObject`

## Usage

### Basic Usage

```bash
# Transcribe an audio file with default settings
stt-cli transcribe audio.wav

# Transcribe a video file (automatically converts to audio)
stt-cli transcribe video.mp4

# Specify custom speaker range (up to 30 speakers)
stt-cli transcribe --min-speakers 2 --max-speakers 8 audio.wav

# Use specific languages for detection
stt-cli transcribe --languages he-IL --languages en-US audio.wav

# Output in JSON format
stt-cli transcribe --output-format json audio.wav

# Save output to file
stt-cli transcribe --output-file transcript.txt audio.wav
```

### Advanced Usage

```bash
# Detailed output with confidence scores
stt-cli transcribe --output-format detailed audio.wav

# Use specific AWS credentials and region
stt-cli transcribe \
  --aws-access-key-id YOUR_KEY \
  --aws-secret-access-key YOUR_SECRET \
  --aws-region us-west-2 \
  audio.wav

# Process with specific speaker count and languages
stt-cli transcribe \
  --min-speakers 2 \
  --max-speakers 5 \
  --languages he-IL \
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
- `--min-speakers INTEGER`: Minimum number of speakers (1-30, default: 1)
- `--max-speakers INTEGER`: Maximum number of speakers (1-30, default: 6)
- `--languages TEXT`: Languages to detect (up to 4). Use language codes like 'he-IL', 'en-US'
- `--output-format [text|json|detailed]`: Output format (default: text)
- `--output-file PATH`: Output file path (default: stdout)
- `--aws-access-key-id TEXT`: AWS access key ID
- `--aws-secret-access-key TEXT`: AWS secret access key
- `--aws-region TEXT`: AWS region (default: us-east-1)
- `--s3-bucket TEXT`: S3 bucket name for audio uploads (optional)
- `--debug`: Enable debug logging

## Supported File Formats

### Audio Formats (Direct Support)

- **WAV** (.wav) - Waveform Audio File Format
- **MP3** (.mp3) - MPEG Audio Layer III
- **MP4** (.mp4) - MPEG-4 Audio
- **M4A** (.m4a) - MPEG-4 Audio (Apple format)
- **FLAC** (.flac) - Free Lossless Audio Codec
- **OGG** (.ogg) - Ogg Vorbis
- **AMR** (.amr) - Adaptive Multi-Rate
- **WebM** (.webm) - WebM Audio

### Video Formats (Automatic Conversion via ffmpeg)

- **AVI** (.avi) - Audio Video Interleave
- **MOV** (.mov) - QuickTime Movie
- **MKV** (.mkv) - Matroska Video
- **FLV** (.flv) - Flash Video
- **WMV** (.wmv) - Windows Media Video
- **MPG/MPEG** (.mpg, .mpeg) - Moving Picture Experts Group
- **3GP** (.3gp) - 3GPP Multimedia
- **M4V** (.m4v) - MPEG-4 Video

When a video file is provided, the audio track is automatically extracted and converted to MP3 format for transcription.

## Output Formats

### Text Format (Default)
```
[Speaker 0]
Hello, how are you today?

[Speaker 1]
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
        "speaker_tag": 0,
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
  Speaker: Speaker 0
  Language: en-US
  Confidence: 95%
  Transcript: Hello, how are you today?
```

## Language Support

The CLI supports automatic detection of multiple languages. Default languages are Hebrew (he-IL) and English (en-US), but you can specify up to 4 different languages:

```bash
# Detect Hebrew and English (default)
stt-cli transcribe audio.wav

# Detect Hebrew, English, Spanish, and French
stt-cli transcribe --languages he-IL --languages en-US --languages es-ES --languages fr-FR audio.wav
```

Common language codes:
- `he-IL` - Hebrew (Israel)
- `en-US` - English (US)
- `es-ES` - Spanish (Spain)
- `fr-FR` - French (France)
- `de-DE` - German (Germany)

## Environment Variables

- `AWS_ACCESS_KEY_ID`: AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `STT_CLI_S3_BUCKET`: S3 bucket name for audio uploads

## File Processing

All audio files are automatically uploaded to Amazon S3 for processing by AWS Transcribe. The CLI handles:

1. **Automatic S3 bucket creation** (if not specified)
2. **File upload** to S3 with appropriate content type
3. **Transcription job management** (start, monitor, retrieve results)
4. **Cleanup** of temporary files and transcription jobs

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

- Requires AWS credentials and active billing account
- Audio files are temporarily uploaded to S3 (cleaned up after processing)
- Processing time depends on file size and AWS Transcribe queue
- Language detection is limited to 4 languages per request
- Maximum 30 speakers for diarization

## Support

For issues and feature requests, please visit the project repository.

## License

This project is licensed under the MIT License.