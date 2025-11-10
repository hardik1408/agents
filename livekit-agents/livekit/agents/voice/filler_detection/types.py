"""
Data types and structures for filler detection.
"""

from dataclasses import dataclass, field
from typing import Literal


InterruptionDecision = Literal["IGNORE", "ALLOW"]


@dataclass
class FillerDetectionMetadata:

    reason: str

    matched_fillers: list[str] = field(default_factory=list)

    non_filler_words: list[str] = field(default_factory=list)

    confidence: float = 1.0

    non_filler_ratio: float = 0.0

    agent_speaking: bool = False


@dataclass
class FillerStats:
    """Statistics tracking for filler detection performance"""

    ignored_filler_count: int = 0

    allowed_interruption_count: int = 0

    allowed_agent_quiet: int = 0

    low_confidence_ignored: int = 0

    def get_summary(self) -> dict:
        """Get a summary of statistics as a dictionary"""
        total = (
            self.ignored_filler_count
            + self.allowed_interruption_count
            + self.allowed_agent_quiet
        )
        return {
            "total_events": total,
            "ignored_fillers": self.ignored_filler_count,
            "allowed_interruptions": self.allowed_interruption_count,
            "allowed_agent_quiet": self.allowed_agent_quiet,
            "low_confidence_ignored": self.low_confidence_ignored,
            "ignore_rate": self.ignored_filler_count / total if total > 0 else 0.0,
        }

    def reset(self) -> None:
        """Reset all statistics to zero"""
        self.ignored_filler_count = 0
        self.allowed_interruption_count = 0
        self.allowed_agent_quiet = 0
        self.low_confidence_ignored = 0