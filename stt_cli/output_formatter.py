"""Output formatting for transcription results."""

import json

from .speech_client import TranscriptionResult


class OutputFormatter:
    """Formats transcription results in various output formats."""

    def __init__(self):
        """Initialize the output formatter."""
        pass

    def format_result(self, results: list[TranscriptionResult], format_type: str) -> str:
        """Format transcription results.

        Args:
            results: List of transcription results
            format_type: Output format ('text', 'json', 'detailed')

        Returns:
            Formatted string output
        """
        if not results:
            return "No transcription results found."

        if format_type == "text":
            return self._format_text(results)
        elif format_type == "json":
            return self._format_json(results)
        elif format_type == "detailed":
            return self._format_detailed(results)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def _format_text(self, results: list[TranscriptionResult]) -> str:
        """Format results as simple text with speaker labels.

        Args:
            results: List of transcription results

        Returns:
            Plain text format with speaker labels
        """
        lines = []
        current_speaker = "INITIAL"  # Use sentinel value to ensure first speaker is always shown

        for result in results:
            speaker_label = f"Speaker {result.speaker_tag}" if result.speaker_tag else "Unknown Speaker"

            # Group consecutive segments from the same speaker
            if result.speaker_tag != current_speaker:
                if lines:  # Add empty line between speakers
                    lines.append("")
                lines.append(f"[{speaker_label}]")
                current_speaker = result.speaker_tag

            lines.append(result.transcript)

        return "\n".join(lines)

    def _format_json(self, results: list[TranscriptionResult]) -> str:
        """Format results as JSON.

        Args:
            results: List of transcription results

        Returns:
            JSON formatted string
        """
        data = {
            "transcription": {
                "segments": [],
                "summary": {
                    "total_segments": len(results),
                    "speakers": len({r.speaker_tag for r in results if r.speaker_tag}),
                    "languages": list({r.language_code for r in results if r.language_code != "unknown"}),
                }
            }
        }

        for i, result in enumerate(results):
            segment = {
                "id": i + 1,
                "transcript": result.transcript,
                "confidence": result.confidence,
                "speaker_tag": result.speaker_tag,
                "language_code": result.language_code,
            }
            data["transcription"]["segments"].append(segment)

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_detailed(self, results: list[TranscriptionResult]) -> str:
        """Format results with detailed information.

        Args:
            results: List of transcription results

        Returns:
            Detailed text format with metadata
        """
        lines = []

        # Summary
        speakers = {r.speaker_tag for r in results if r.speaker_tag}
        languages = {r.language_code for r in results if r.language_code != "unknown"}

        lines.append("=== TRANSCRIPTION SUMMARY ===")
        lines.append(f"Total segments: {len(results)}")
        lines.append(f"Speakers detected: {len(speakers)}")
        lines.append(f"Languages detected: {', '.join(languages) if languages else 'Unknown'}")
        lines.append("")

        # Detailed segments
        lines.append("=== DETAILED TRANSCRIPTION ===")
        lines.append("")

        for i, result in enumerate(results, 1):
            speaker_label = f"Speaker {result.speaker_tag}" if result.speaker_tag else "Unknown"
            confidence_pct = int(result.confidence * 100) if result.confidence else 0

            lines.append(f"Segment {i}:")
            lines.append(f"  Speaker: {speaker_label}")
            lines.append(f"  Language: {result.language_code}")
            lines.append(f"  Confidence: {confidence_pct}%")
            lines.append(f"  Transcript: {result.transcript}")
            lines.append("")

        return "\n".join(lines)

    def _group_by_speaker(self, results: list[TranscriptionResult]) -> dict[int, list[TranscriptionResult]]:
        """Group results by speaker.

        Args:
            results: List of transcription results

        Returns:
            Dictionary mapping speaker_tag to list of results
        """
        groups = {}
        for result in results:
            speaker_tag = result.speaker_tag or 0  # Use 0 for unknown speakers
            if speaker_tag not in groups:
                groups[speaker_tag] = []
            groups[speaker_tag].append(result)

        return groups
