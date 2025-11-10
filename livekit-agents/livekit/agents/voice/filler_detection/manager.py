"""
Main coordinator for filler detection integration with LiveKit agents.
"""

import logging
from typing import TYPE_CHECKING, Tuple

from .config import FillerDetectionConfig
from .detector import FillerDetector
from .types import FillerDetectionMetadata, FillerStats

if TYPE_CHECKING:
    from ..agent_session import AgentSession


class FillerDetectionManager:
    """
    Main coordinator for filler detection.
    Integrates with AgentSession to make interruption decisions.
    """

    def __init__(self, config: FillerDetectionConfig, session: "AgentSession"):
        """
        Initialize the filler detection manager.
        """
        self.config = config
        self.session = session
        self.detector = FillerDetector(config)

        # Statistics tracking
        self.stats = FillerStats()

        # Setup logging
        self._logger = logging.getLogger("livekit.agents.filler_detection")
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure the logger based on config settings"""
        if self.config.enable_logging:
            level = getattr(logging, self.config.log_level, logging.INFO)
            self._logger.setLevel(level)

            # Only add handler if none exists
            if not self._logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    "[%(name)s] %(levelname)s: %(message)s"
                )
                handler.setFormatter(formatter)
                self._logger.addHandler(handler)
        else:
            self._logger.setLevel(logging.CRITICAL)

    def should_ignore_interruption(
        self, transcript: str, confidence: float, is_final: bool
    ) -> Tuple[bool, FillerDetectionMetadata]:
        """
        Determine whether to ignore an interruption based on the transcript.

        This is the main decision point for filler detection. It checks:
        1. Whether the agent is currently speaking
        2. Whether the transcript contains only filler words
        3. Confidence scores and other factors
        """
        # Check if agent is speaking
        agent_speaking = self.session.agent_state == "speaking"

        # If only_when_agent_speaking is enabled and agent is NOT speaking,
        # never ignore (always allow user speech when agent is quiet)
        if self.config.only_when_agent_speaking and not agent_speaking:
            self.stats.allowed_agent_quiet += 1
            metadata = FillerDetectionMetadata(
                reason="agent_quiet",
                confidence=confidence,
                agent_speaking=False,
                matched_fillers=[],
                non_filler_words=[],
            )
            self._log_decision("ALLOW", transcript, metadata, is_final)
            return (False, metadata)

        # Agent IS speaking (or mode allows checking regardless)
        # Check if transcript is filler-only
        is_filler, metadata = self.detector.is_filler_only(transcript, confidence)
        metadata.agent_speaking = agent_speaking

        if is_filler:
            # IGNORE - filler detected while agent speaking
            self.stats.ignored_filler_count += 1
            if metadata.reason == "low_confidence":
                self.stats.low_confidence_ignored += 1
            self._log_decision("IGNORE", transcript, metadata, is_final)
            return (True, metadata)
        else:
            # ALLOW - real speech detected, interrupt agent
            self.stats.allowed_interruption_count += 1
            self._log_decision("ALLOW", transcript, metadata, is_final)
            return (False, metadata)

    def _log_decision(
        self,
        decision: str,
        transcript: str,
        metadata: FillerDetectionMetadata,
        is_final: bool,
    ) -> None:
        """
        Log an interruption decision for debugging and monitoring.
        """
        if not self.config.enable_logging:
            return

        transcript_type = "FINAL" if is_final else "INTERIM"
        agent_state = self.session.agent_state

        # Format log message
        log_msg = (
            f"[{decision}] [{transcript_type}] "
            f"transcript='{transcript}' | "
            f"agent_state={agent_state} | "
            f"reason={metadata.reason} | "
            f"confidence={metadata.confidence:.2f}"
        )

        # Add additional context based on reason
        if metadata.matched_fillers:
            log_msg += f" | fillers={metadata.matched_fillers}"
        if metadata.non_filler_words:
            log_msg += f" | non_fillers={metadata.non_filler_words}"
        if metadata.non_filler_ratio > 0:
            log_msg += f" | ratio={metadata.non_filler_ratio:.2f}"

        # Log at appropriate level
        if decision == "IGNORE":
            self._logger.info(log_msg)
        else:
            self._logger.debug(log_msg)

    def get_stats(self) -> dict:
        """
        Get current statistics as a dictionary.
        """
        return self.stats.get_summary()

    def reset_stats(self) -> None:
        """Reset all statistics counters"""
        self.stats.reset()

    def update_ignored_words(self, words: list[str]) -> None:
        """
        Update the list of ignored filler words.
        """
        self.detector.update_ignored_words(words)
        self._logger.info(f"Updated ignored words list: {words}")

    def add_ignored_words(self, words: list[str]) -> None:
        """
        Add words to the ignored filler words list.
        """
        self.detector.add_ignored_words(words)
        self._logger.info(f"Added ignored words: {words}")

    def remove_ignored_words(self, words: list[str]) -> None:
        """
        Remove words from the ignored filler words list.
        """
        self.detector.remove_ignored_words(words)
        self._logger.info(f"Removed ignored words: {words}")