"""AWS Transcribe client wrapper with speaker diarization."""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger(__name__)


class AudioConfig:
    """Configuration for audio input."""
    
    def __init__(
        self,
        content: Optional[bytes] = None,
        uri: Optional[str] = None,
        media_format: str = "mp3",
        sample_rate: Optional[int] = None,
    ):
        self.content = content
        self.uri = uri
        self.media_format = media_format
        self.sample_rate = sample_rate


class TranscriptionResult:
    """Result of speech transcription with speaker information."""
    
    def __init__(self, transcript: str, confidence: float, language_code: str, speaker_tag: Optional[int] = None):
        self.transcript = transcript
        self.confidence = confidence
        self.language_code = language_code
        self.speaker_tag = speaker_tag


class SpeechClient:
    """AWS Transcribe client with speaker diarization support."""
    
    def __init__(self, aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None, 
                 aws_region: str = "us-east-1", bucket_name: Optional[str] = None):
        """Initialize the AWS Transcribe client.
        
        Args:
            aws_access_key_id: AWS access key ID. If None, uses default AWS credentials.
            aws_secret_access_key: AWS secret access key. If None, uses default AWS credentials.
            aws_region: AWS region for services.
            bucket_name: S3 bucket name for audio uploads.
        """
        # Initialize AWS clients
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        self.transcribe_client = session.client('transcribe')
        self.s3_client = session.client('s3')
        self.aws_region = aws_region
        self.bucket_name = bucket_name
        self._temp_bucket = None
    
    def transcribe(
        self,
        audio_config: AudioConfig,
        min_speakers: int = 1,
        max_speakers: int = 6,
        languages: list[str] | None = None,
    ) -> list[TranscriptionResult]:
        """Transcribe audio with speaker diarization and language detection.
        
        Args:
            audio_config: Audio configuration
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            languages: List of language codes for transcription
            
        Returns:
            List of transcription results with speaker information
        """
        if languages is None:
            languages = ["he-IL", "en-US"]  # Hebrew first for better detection
        
        # Prepare audio for transcription
        if audio_config.content:
            # Upload to S3 and get URI
            s3_uri = self._upload_to_s3(audio_config.content, audio_config.media_format)
        elif audio_config.uri:
            s3_uri = audio_config.uri
        else:
            raise ValueError("Either audio content or URI must be provided")
        
        # Start transcription job
        job_name = f"stt-cli-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        
        try:
            # Configure transcription job
            job_config = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': s3_uri},
                'MediaFormat': audio_config.media_format,
                'LanguageCode': self._convert_language_code(languages[0]),
                'Settings': {
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': max_speakers,
                    'ShowAlternatives': True,
                    'MaxAlternatives': 2,
                }
            }
            
            # Add sample rate if specified
            if audio_config.sample_rate:
                job_config['MediaSampleRateHertz'] = audio_config.sample_rate
            
            # Add language identification if multiple languages
            if len(languages) > 1:
                job_config['IdentifyLanguage'] = True
                job_config['LanguageOptions'] = [self._convert_language_code(lang) for lang in languages[:4]]
                # Remove LanguageCode when using IdentifyLanguage
                del job_config['LanguageCode']
            
            logger.info(f"Starting transcription job: {job_name}")
            self.transcribe_client.start_transcription_job(**job_config)
            
            # Wait for completion
            result = self._wait_for_completion(job_name)
            
            # Clean up temporary S3 file if we uploaded it
            if audio_config.content:
                self._cleanup_s3_file(s3_uri)
            
            return self._parse_response(result)
            
        except Exception as e:
            # Clean up on error
            if audio_config.content:
                try:
                    self._cleanup_s3_file(s3_uri)
                except Exception:
                    pass
            raise e
    
    def _convert_language_code(self, code: str) -> str:
        """Convert language codes to AWS format."""
        # AWS uses different codes for some languages
        conversion_map = {
            'iw-IL': 'he-IL',  # AWS uses he-IL for Hebrew
            'he-IL': 'he-IL',
        }
        return conversion_map.get(code, code)
    
    def _get_or_create_bucket(self) -> str:
        """Get or create an S3 bucket for audio uploads."""
        if self.bucket_name:
            return self.bucket_name
            
        if self._temp_bucket:
            return self._temp_bucket
            
        # Create bucket name
        bucket_name = f"stt-cli-audio-{uuid.uuid4().hex[:8]}"
        
        try:
            # Create bucket
            if self.aws_region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                )
            
            self._temp_bucket = bucket_name
            logger.debug(f"Created S3 bucket: {bucket_name}")
            return bucket_name
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyExists':
                # Try with a different name
                bucket_name = f"stt-cli-audio-{uuid.uuid4().hex[:12]}"
                if self.aws_region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                    )
                self._temp_bucket = bucket_name
                return bucket_name
            else:
                raise ValueError(f"Failed to create S3 bucket: {e}")
    
    def _upload_to_s3(self, content: bytes, media_format: str) -> str:
        """Upload audio content to S3 and return the URI."""
        bucket_name = self._get_or_create_bucket()
        filename = f"audio-{uuid.uuid4().hex}.{media_format}"
        
        try:
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=filename,
                Body=content,
                ContentType=f"audio/{media_format}"
            )
            
            uri = f"s3://{bucket_name}/{filename}"
            logger.debug(f"Uploaded audio to: {uri}")
            return uri
            
        except ClientError as e:
            raise ValueError(f"Failed to upload audio to S3: {e}")
    
    def _cleanup_s3_file(self, s3_uri: str):
        """Clean up temporary file from S3."""
        try:
            if s3_uri.startswith("s3://"):
                # Parse S3 URI
                parts = s3_uri[5:].split("/", 1)
                if len(parts) == 2:
                    bucket_name, key = parts
                    self.s3_client.delete_object(Bucket=bucket_name, Key=key)
                    logger.debug(f"Cleaned up S3 file: {s3_uri}")
        except Exception as e:
            logger.warning(f"Failed to cleanup S3 file {s3_uri}: {e}")
    
    def _wait_for_completion(self, job_name: str, timeout: int = 600) -> dict:
        """Wait for transcription job to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    logger.info(f"Transcription job {job_name} completed")
                    return response['TranscriptionJob']
                elif status == 'FAILED':
                    reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    raise ValueError(f"Transcription job failed: {reason}")
                
                # Wait before checking again
                time.sleep(5)
                
            except Exception as e:
                if 'does not exist' in str(e).lower():
                    raise ValueError(f"Transcription job {job_name} not found")
                raise e
        
        raise TimeoutError(f"Transcription job {job_name} timed out after {timeout} seconds")
    
    def _parse_response(self, job_result: dict) -> list[TranscriptionResult]:
        """Parse AWS Transcribe response into TranscriptionResult objects."""
        results = []
        
        # Get transcript URL
        transcript_uri = job_result['Transcript']['TranscriptFileUri']
        
        # Download and parse transcript
        import urllib.request
        with urllib.request.urlopen(transcript_uri) as response:
            transcript_data = json.loads(response.read().decode())
        
        # Extract language code
        language_code = job_result.get('LanguageCode', 'unknown')
        
        # Check if we have speaker labels
        if 'speaker_labels' in transcript_data['results']:
            # Parse speaker segments
            speaker_segments = transcript_data['results']['speaker_labels']['segments']
            items = transcript_data['results']['items']
            
            for segment in speaker_segments:
                speaker_label = segment['speaker_label']
                start_time = float(segment['start_time'])
                end_time = float(segment['end_time'])
                
                # Find corresponding words/items
                segment_items = []
                for item in items:
                    if item['type'] == 'pronunciation' and 'start_time' in item:
                        item_start = float(item['start_time'])
                        if start_time <= item_start <= end_time:
                            segment_items.append(item)
                
                if segment_items:
                    # Build transcript from items
                    transcript_parts = []
                    confidences = []
                    
                    for item in segment_items:
                        transcript_parts.append(item['alternatives'][0]['content'])
                        confidences.append(float(item['alternatives'][0]['confidence']))
                    
                    transcript = ' '.join(transcript_parts)
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    
                    # Convert speaker_label to int (remove 'spk_' prefix)
                    try:
                        speaker_tag = int(speaker_label.replace('spk_', ''))
                    except (ValueError, AttributeError):
                        speaker_tag = None
                    
                    results.append(TranscriptionResult(
                        transcript=transcript,
                        confidence=avg_confidence,
                        language_code=language_code,
                        speaker_tag=speaker_tag,
                    ))
        else:
            # No speaker diarization, return full transcript
            if 'transcripts' in transcript_data['results']:
                full_transcript = transcript_data['results']['transcripts'][0]['transcript']
                
                # Calculate average confidence
                items = transcript_data['results']['items']
                confidences = []
                for item in items:
                    if item['type'] == 'pronunciation':
                        confidences.append(float(item['alternatives'][0]['confidence']))
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                results.append(TranscriptionResult(
                    transcript=full_transcript,
                    confidence=avg_confidence,
                    language_code=language_code,
                    speaker_tag=None,
                ))
        
        # Clean up transcription job
        try:
            self.transcribe_client.delete_transcription_job(
                TranscriptionJobName=job_result['TranscriptionJobName']
            )
        except Exception as e:
            logger.warning(f"Failed to delete transcription job: {e}")
        
        return results