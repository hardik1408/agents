import os
from dataclasses import dataclass, field

@dataclass
class FillerDetectionConfig:
    """Configuration for filler word detection and filtering"""

    ignored_words: list[str] = field(
        default_factory=lambda: [
            "uh",
            "um",
            "umm",
            "hmm",
            "haan",
            "ah",
            "eh",
            "er",
            "mm",
            "mhm",
        ]
    )

    min_confidence_threshold: float = 0.3
    case_insensitive: bool = True
    only_when_agent_speaking: bool = True
    non_filler_ratio_threshold: float = 0.3
    enable_logging: bool = True
    allow_dynamic_updates: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "FillerDetectionConfig":
        """
        Load configuration from environment variables.
        """
        ignored_words_str = os.getenv(
            "FILLER_IGNORED_WORDS", "uh,um,umm,hmm,haan,ah,eh,er,mm,mhm"
        )
        ignored_words = [w.strip() for w in ignored_words_str.split(",") if w.strip()]

        return cls(
            ignored_words=ignored_words,
            min_confidence_threshold=float(
                os.getenv("FILLER_MIN_CONFIDENCE", "0.3")
            ),
            non_filler_ratio_threshold=float(
                os.getenv("FILLER_NON_FILLER_RATIO", "0.3")
            ),
            enable_logging=os.getenv("FILLER_ENABLE_LOGGING", "true").lower()
            == "true",
            case_insensitive=os.getenv("FILLER_CASE_INSENSITIVE", "true").lower()
            == "true",
            log_level=os.getenv("FILLER_LOG_LEVEL", "INFO").upper(),
        )

    def add_ignored_words(self, words: list[str]) -> None:
        """Add new words to the ignored words list"""
        if not self.allow_dynamic_updates:
            raise ValueError("Dynamic updates are not enabled in configuration")
        self.ignored_words.extend(words)

    def remove_ignored_words(self, words: list[str]) -> None:
        """Remove words from the ignored words list"""
        if not self.allow_dynamic_updates:
            raise ValueError("Dynamic updates are not enabled in configuration")
        self.ignored_words = [w for w in self.ignored_words if w not in words]

    def set_ignored_words(self, words: list[str]) -> None:
        """Replace the entire ignored words list"""
        if not self.allow_dynamic_updates:
            raise ValueError("Dynamic updates are not enabled in configuration")
        self.ignored_words = words