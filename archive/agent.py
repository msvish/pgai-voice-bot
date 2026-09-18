import logging

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli
from livekit.plugins import cartesia, deepgram, openai, silero

load_dotenv(override=True)

logger = logging.getLogger("pgai-voice-bot")

server = AgentServer()


class PassthroughAgent(Agent):
    """Minimal test agent: repeats back exactly what it hears.
    Proves the pipeline round-trips audio before real caller logic is added."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a test agent. Repeat back exactly what the user "
                "just said, word for word, then stop talking."
            )
        )


@server.rtc_session(agent_name="pgai-caller")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-3"),
    )

    await session.start(agent=PassthroughAgent(), room=ctx.room)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)