"""Google Cloud Speech-to-Text client wrapper with speaker diarization."""

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from google.oauth2 import service_account


class AudioConfig:
    """Configuration for audio input."""

    def __init__(
        self,
        content: Optional[bytes] = None,
        uri: Optional[str] = None,
        encoding: speech.RecognitionConfig.AudioEncoding = speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz: int = 16000,
        audio_channel_count: int = 1,
    ):
        self.content = content
        self.uri = uri
        self.encoding = encoding
        self.sample_rate_hertz = sample_rate_hertz
        self.audio_channel_count = audio_channel_count


class TranscriptionResult:
    """Result of speech transcription with speaker information."""

    def __init__(self, transcript: str, confidence: float, language_code: str, speaker_tag: Optional[int] = None):
        self.transcript = transcript
        self.confidence = confidence
        self.language_code = language_code
        self.speaker_tag = speaker_tag


class SpeechClient:
    """Google Cloud Speech-to-Text client with advanced features."""

    def __init__(self, credentials_path: Optional[Path] = None, bucket_name: Optional[str] = None):
        """Initialize the Speech client.

        Args:
            credentials_path: Path to service account JSON file.
                            If None, uses Application Default Credentials.
            bucket_name: GCS bucket name for large file uploads.
                        If None, will try to create a temporary bucket.
        """
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                str(credentials_path)
            )
            self.speech_client = speech.SpeechClient(credentials=credentials)
            self.storage_client = storage.Client(credentials=credentials)
        else:
            # Use Application Default Credentials
            self.speech_client = speech.SpeechClient()
            self.storage_client = storage.Client()
        
        self.bucket_name = bucket_name
        self._temp_bucket = None

    def transcribe(
        self,
        audio_config: AudioConfig,
        min_speakers: int = 1,
        max_speakers: int = 6,
        languages: list[str] = None,
    ) -> list[TranscriptionResult]:
        """Transcribe audio with speaker diarization and language detection.

        Args:
            audio_config: Audio configuration
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            languages: List of language codes for automatic detection

        Returns:
            List of transcription results with speaker information
        """
        if languages is None:
            languages = ["iw-IL", "en-US"]  # Hebrew first for better detection (iw-IL is correct code)

        # Configure speaker diarization
        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=min_speakers,
            max_speaker_count=max_speakers,
        )

        # Configure recognition with better settings for Hebrew/multilingual
        config = speech.RecognitionConfig(
            encoding=audio_config.encoding,
            sample_rate_hertz=audio_config.sample_rate_hertz,
            audio_channel_count=audio_config.audio_channel_count,
            language_code=languages[0],  # Primary language
            alternative_language_codes=languages[1:] if len(languages) > 1 else [],
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,  # Better for diarization
            enable_word_confidence=True,    # Better confidence tracking
            diarization_config=diarization_config,
            model="default",  # Use default model for better language support
        )

        # Prepare audio input
        if audio_config.content:
            # Check file size - upload to GCS for files > 10MB
            if len(audio_config.content) > 10 * 1024 * 1024:  # 10MB limit
                # Upload to Cloud Storage and use URI
                uri = self._upload_to_gcs(audio_config.content)
                audio = speech.RecognitionAudio(uri=uri)
                operation = self.speech_client.long_running_recognize(config=config, audio=audio)
                response = operation.result(timeout=1200)  # 20 minute timeout for large files
                # Clean up temporary file
                self._cleanup_gcs_file(uri)
            else:
                # Use synchronous recognition for smaller files
                audio = speech.RecognitionAudio(content=audio_config.content)
                response = self.speech_client.recognize(config=config, audio=audio)
        elif audio_config.uri:
            audio = speech.RecognitionAudio(uri=audio_config.uri)
            # Use long-running recognition for GCS files
            operation = self.speech_client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=1200)  # 20 minute timeout
        else:
            raise ValueError("Either audio content or URI must be provided")

        return self._parse_response(response)

    def _parse_response(self, response) -> list[TranscriptionResult]:
        """Parse the Speech API response into TranscriptionResult objects."""
        results = []

        for result in response.results:
            if not result.alternatives:
                continue

            alternative = result.alternatives[0]

            # Extract speaker information if available
            speaker_tag = None
            if hasattr(result, 'speaker_tag'):
                speaker_tag = result.speaker_tag
            elif hasattr(alternative, 'words') and alternative.words:
                # Get speaker tag from words (speaker diarization info is in words)
                for word in alternative.words:
                    if hasattr(word, 'speaker_tag') and word.speaker_tag is not None:
                        speaker_tag = word.speaker_tag
                        break

            # Determine language
            language_code = "unknown"
            if hasattr(result, 'language_code'):
                language_code = result.language_code
            elif hasattr(alternative, 'language_code'):
                language_code = alternative.language_code

            results.append(TranscriptionResult(
                transcript=alternative.transcript.strip(),
                confidence=alternative.confidence,
                language_code=language_code,
                speaker_tag=speaker_tag,
            ))

        return results

    def _get_or_create_bucket(self) -> str:
        """Get or create a bucket for file uploads."""
        if self.bucket_name:
            return self.bucket_name
            
        if self._temp_bucket:
            return self._temp_bucket
            
        # Create bucket name based on project ID
        project_id = self.storage_client.project
        if not project_id:
            raise ValueError("No project ID found. Please set up Google Cloud credentials properly.")
            
        # Use consistent bucket name derived from project ID
        bucket_name = f"{project_id}-stt-cli-audio"
        
        try:
            # Check if bucket already exists
            bucket = self.storage_client.bucket(bucket_name)
            if bucket.exists():
                self._temp_bucket = bucket_name
                return bucket_name
                
            # Create bucket in us-central1 (good for Speech API)
            bucket.create(location="us-central1")
            self._temp_bucket = bucket_name
            return bucket_name
        except Exception as e:
            # If creation fails, it might already exist (race condition) - try to use it
            bucket = self.storage_client.bucket(bucket_name)
            if bucket.exists():
                self._temp_bucket = bucket_name
                return bucket_name
            else:
                raise ValueError(f"Failed to create or access bucket {bucket_name}: {e}")

    def _upload_to_gcs(self, content: bytes) -> str:
        """Upload audio content to Google Cloud Storage and return the URI."""
        bucket_name = self._get_or_create_bucket()
        filename = f"audio-{uuid.uuid4().hex}.m4a"
        
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        # Upload the file
        blob.upload_from_string(content, content_type="audio/mp4")
        
        return f"gs://{bucket_name}/{filename}"

    def _cleanup_gcs_file(self, uri: str):
        """Clean up temporary file from GCS."""
        try:
            # Parse the URI to get bucket and filename
            if uri.startswith("gs://"):
                path_parts = uri[5:].split("/", 1)
                if len(path_parts) == 2:
                    bucket_name, filename = path_parts
                    bucket = self.storage_client.bucket(bucket_name)
                    blob = bucket.blob(filename)
                    blob.delete()
        except Exception:
            # Ignore cleanup errors
            pass
