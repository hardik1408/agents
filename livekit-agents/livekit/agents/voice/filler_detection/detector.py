import re
from typing import Tuple

from .config import FillerDetectionConfig
from .types import FillerDetectionMetadata


class FillerDetector:
    """
    Detects whether a transcript contains only filler words or real speech.
    """

    def __init__(self, config: FillerDetectionConfig):
        """
        Initialize the filler detector.

        Args:
            config: Configuration for filler detection
        """
        self.config = config
        self._normalized_fillers: set[str] = self._normalize_fillers()

    def is_filler_only(
        self, transcript: str, confidence: float = 1.0
    ) -> Tuple[bool, FillerDetectionMetadata]:
        """
        Determine if the transcript contains only filler words.
        """
        # Check confidence threshold
        if confidence < self.config.min_confidence_threshold:
            return (
                True,
                FillerDetectionMetadata(
                    reason="low_confidence",
                    confidence=confidence,
                    matched_fillers=[],
                    non_filler_words=[],
                ),
            )

        # Handle empty transcript
        if not transcript or not transcript.strip():
            return (
                True,
                FillerDetectionMetadata(
                    reason="empty_transcript",
                    confidence=confidence,
                    matched_fillers=[],
                    non_filler_words=[],
                ),
            )

        # Tokenize transcript into words
        words = self._tokenize(transcript)

        if not words:
            return (
                True,
                FillerDetectionMetadata(
                    reason="no_words_detected",
                    confidence=confidence,
                    matched_fillers=[],
                    non_filler_words=[],
                ),
            )

        # Classify each word as filler or non-filler
        filler_words = []
        non_filler_words = []

        for word in words:
            if self._is_filler_word(word):
                filler_words.append(word)
            else:
                non_filler_words.append(word)

        # Decision logic
        total_words = len(words)
        non_filler_count = len(non_filler_words)

        # Pure filler: no real words detected
        if non_filler_count == 0:
            return (
                True,
                FillerDetectionMetadata(
                    reason="pure_filler",
                    matched_fillers=filler_words,
                    non_filler_words=[],
                    confidence=confidence,
                    non_filler_ratio=0.0,
                ),
            )

        # Mixed content: calculate ratio
        non_filler_ratio = non_filler_count / total_words

        # Mostly fillers: ratio below threshold
        if non_filler_ratio < self.config.non_filler_ratio_threshold:
            return (
                True,
                FillerDetectionMetadata(
                    reason="mostly_filler",
                    matched_fillers=filler_words,
                    non_filler_words=non_filler_words,
                    confidence=confidence,
                    non_filler_ratio=non_filler_ratio,
                ),
            )

        # Real speech: sufficient non-filler content
        return (
            False,
            FillerDetectionMetadata(
                reason="real_speech",
                matched_fillers=filler_words,
                non_filler_words=non_filler_words,
                confidence=confidence,
                non_filler_ratio=non_filler_ratio,
            ),
        )

    def _is_filler_word(self, word: str) -> bool:
        """
        Check if a word is in the filler list.
        """
        if self.config.case_insensitive:
            normalized = word.lower().strip()
        else:
            normalized = word.strip()

        return normalized in self._normalized_fillers

    def _tokenize(self, transcript: str) -> list[str]:
        """
        Split transcript into individual words.
        """
        # Use regex to extract word characters, handling various languages
        # \w matches [a-zA-Z0-9_] and Unicode word characters
        words = re.findall(r"\b\w+\b", transcript)

        return words

    def _normalize_fillers(self) -> set[str]:
        """
        Normalize the filler words list for efficient matching.
        """
        if self.config.case_insensitive:
            return {word.lower().strip() for word in self.config.ignored_words}
        else:
            return {word.strip() for word in self.config.ignored_words}

    def update_ignored_words(self, words: list[str]) -> None:
        """
        Update the list of ignored filler words.
        """
        if not self.config.allow_dynamic_updates:
            raise ValueError(
                "Dynamic updates are not enabled. "
                "Set allow_dynamic_updates=True in config."
            )

        self.config.ignored_words = words
        self._normalized_fillers = self._normalize_fillers()

    def add_ignored_words(self, words: list[str]) -> None:
        """
        Add words to the ignored filler words list.
        """
        if not self.config.allow_dynamic_updates:
            raise ValueError(
                "Dynamic updates are not enabled. "
                "Set allow_dynamic_updates=True in config."
            )

        self.config.add_ignored_words(words)
        self._normalized_fillers = self._normalize_fillers()

    def remove_ignored_words(self, words: list[str]) -> None:
        """
        Remove words from the ignored filler words list.
        """
        if not self.config.allow_dynamic_updates:
            raise ValueError(
                "Dynamic updates are not enabled. "
                "Set allow_dynamic_updates=True in config."
            )

        self.config.remove_ignored_words(words)
        self._normalized_fillers = self._normalize_fillers()