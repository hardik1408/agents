import asyncio
import logging

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice import VoiceAgent
from livekit.agents.voice.agent_activity_extended import FillerAwareAgentActivity
from livekit.agents.voice.filler_detection import FillerDetectionConfig
from livekit.plugins import deepgram, openai, silero

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the voice agent with filler detection.
    """
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Configure filler detection
    filler_config = FillerDetectionConfig(
        # List of filler words to ignore when agent is speaking
        ignored_words=[
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
        ],
        min_confidence_threshold=0.3,
        # If >30% of words are non-fillers, allow interruption
        non_filler_ratio_threshold=0.3,
        enable_logging=True,
        log_level="INFO",
        allow_dynamic_updates=True,
    )


    # Create the voice agent with filler detection
    agent = VoiceAgent(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(),
        activity_cls=FillerAwareAgentActivity,
        # Pass filler config to the activity
        activity_kwargs={"filler_config": filler_config},
        chat_ctx=llm.ChatContext().append(
            role="system",
            text=(
                "You are a helpful voice assistant. Be conversational and natural. "
                "Keep responses concise since this is voice conversation. "
                "The user may occasionally make filler sounds like 'uh' or 'hmm' "
                "while you're speaking - these will be automatically ignored so you "
                "can continue speaking naturally."
            ),
        ),
    )

    agent.start(ctx.room)

    # Log initial configuration
    logger.info("Voice agent with filler detection started")
    logger.info(f"Ignored words: {filler_config.ignored_words}")
    logger.info(f"Min confidence threshold: {filler_config.min_confidence_threshold}")
    logger.info(
        f"Non-filler ratio threshold: {filler_config.non_filler_ratio_threshold}"
    )

    await agent.say("Hi! I'm a voice assistant with intelligent filler detection.")

    # Monitor statistics periodically
    async def log_stats():
        while True:
            await asyncio.sleep(60)  # Log stats every minute
            if agent.activity and hasattr(agent.activity, "get_filler_stats"):
                stats = agent.activity.get_filler_stats()
                if stats:
                    logger.info(f"Filler detection stats: {stats}")

    asyncio.create_task(log_stats())


def main():
    """Run the agent worker"""
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )


if __name__ == "__main__":
    main()