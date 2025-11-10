from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .. import stt
from .agent_activity import AgentActivity
from .events import UserInputTranscribedEvent
from .filler_detection import FillerDetectionConfig, FillerDetectionManager

if TYPE_CHECKING:
    from .agent import Agent
    from .agent_session import AgentSession


class FillerAwareAgentActivity(AgentActivity):
    """
    Extended AgentActivity with filler detection capability.
    This class extends the base AgentActivity to add intelligent filler word
    detection. It overrides the transcript event handlers to intercept and
    analyze transcripts before triggering interruptions.
    """

    def __init__(
        self,
        session: AgentSession,
        agent: Agent,
        filler_config: FillerDetectionConfig | None = None,
        **kwargs,
    ):
        """
        Initialize the FillerAwareAgentActivity.

        Args:
            session: The AgentSession instance
            agent: The Agent instance
            filler_config: Optional configuration for filler detection.
                          If None, filler detection is disabled.
            **kwargs: Additional arguments passed to parent AgentActivity
        """
        super().__init__(session, agent, **kwargs)

        # Initialize filler detection if config provided
        self._filler_manager: FillerDetectionManager | None = None
        if filler_config is not None:
            self._filler_manager = FillerDetectionManager(
                config=filler_config, session=session
            )

    def on_interim_transcript(
        self, ev: stt.SpeechEvent, *, speaking: bool | None
    ) -> None:
        """
        Override to add filler detection for interim transcripts.

        This method intercepts interim transcripts and checks if they contain
        only filler words. If the agent is speaking and the transcript is
        filler-only, the interruption is prevented.

        Args:
            ev: The speech event containing the transcript
            speaking: Whether the user is currently speaking (from VAD)
        """
        # Check for realtime model first (same as parent)
        from .. import llm

        if isinstance(self.llm, llm.RealtimeModel) and self.llm.capabilities.user_transcription:
            # skip stt transcription if user_transcription is enabled on the realtime model
            return

        # Apply filler detection if enabled
        if self._filler_manager is not None and ev.alternatives:
            transcript = ev.alternatives[0].text
            confidence = ev.alternatives[0].confidence

            should_ignore, metadata = self._filler_manager.should_ignore_interruption(
                transcript=transcript, confidence=confidence, is_final=False
            )

            # Always emit the transcription event for observability
            self._session._user_input_transcribed(
                UserInputTranscribedEvent(
                    language=ev.alternatives[0].language,
                    transcript=transcript,
                    is_final=False,
                    speaker_id=ev.alternatives[0].speaker_id,
                ),
            )

            if should_ignore:
                # Filler detected - skip interruption logic
                return

        # Call parent implementation (normal interruption flow)
        # We do this by manually calling the parent's logic that would have
        # been executed, but we already called _user_input_transcribed above,
        # so we only need to handle the interruption logic
        if self._filler_manager is None:
            # If no filler manager, use default parent behavior
            super().on_interim_transcript(ev, speaking=speaking)
        else:
            # We already emitted the event, now just do the interruption check
            if ev.alternatives[0].text:
                self._interrupt_by_audio_activity()

                if (
                    speaking is False
                    and self._paused_speech
                    and (
                        timeout := self._session.options.false_interruption_timeout
                    )
                    is not None
                ):
                    # schedule a resume timer if interrupted after end_of_speech
                    self._start_false_interruption_timer(timeout)

    def on_final_transcript(self, ev: stt.SpeechEvent) -> None:
        """
        Override to add filler detection for final transcripts.

        This method intercepts final transcripts and checks if they contain
        only filler words. If the agent is speaking and the transcript is
        filler-only, the interruption commitment is prevented.

        Args:
            ev: The speech event containing the final transcript
        """
        # Check for realtime model first (same as parent)
        from .. import llm

        if isinstance(self.llm, llm.RealtimeModel) and self.llm.capabilities.user_transcription:
            # skip stt transcription if user_transcription is enabled on the realtime model
            return

        # Apply filler detection if enabled
        if self._filler_manager is not None and ev.alternatives:
            transcript = ev.alternatives[0].text
            confidence = ev.alternatives[0].confidence

            should_ignore, metadata = self._filler_manager.should_ignore_interruption(
                transcript=transcript, confidence=confidence, is_final=True
            )

            # Always emit the transcription event for observability
            self._session._user_input_transcribed(
                UserInputTranscribedEvent(
                    language=ev.alternatives[0].language,
                    transcript=transcript,
                    is_final=True,
                    speaker_id=ev.alternatives[0].speaker_id,
                ),
            )

            if should_ignore:
                # Filler detected - skip interruption commitment logic
                return

        # Call parent implementation (normal interruption flow)
        if self._filler_manager is None:
            # If no filler manager, use default parent behavior
            super().on_final_transcript(ev)
        else:
            # We already emitted the event, now just do the paused speech interruption
            self._interrupt_paused_speech_task = asyncio.create_task(
                self._interrupt_paused_speech(old_task=self._interrupt_paused_speech_task)
            )

    @property
    def filler_manager(self) -> FillerDetectionManager | None:
        """
        Get the filler detection manager instance.

        Returns:
            The FillerDetectionManager if enabled, None otherwise
        """
        return self._filler_manager

    def get_filler_stats(self) -> dict | None:
        """
        Get filler detection statistics.

        Returns:
            Dictionary with statistics if filler detection is enabled,
            None otherwise
        """
        if self._filler_manager is not None:
            return self._filler_manager.get_stats()
        return None

    def reset_filler_stats(self) -> None:
        """Reset filler detection statistics counters"""
        if self._filler_manager is not None:
            self._filler_manager.reset_stats()