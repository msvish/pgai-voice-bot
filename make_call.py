import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from livekit import api

load_dotenv()

logger = logging.getLogger("make-call")
logger.setLevel(logging.INFO)

agent_name = "pgai-caller"
test_number = "+18054398008"
outbound_trunk_id = os.environ["SIP_OUTBOUND_TRUNK_ID"]


async def make_call(scenario: str):
    lkapi = api.LiveKitAPI()
    room_name = f"pgai-{scenario}"
    identity = scenario.replace("_", "-")

    await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(agent_name=agent_name, room=room_name, metadata=scenario)
    )

    try:
        participant = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=test_number,
                sip_number="+15822335108",
                room_name=room_name,
                participant_identity=identity,
                participant_name=identity,
                wait_until_answered=True,
            )
        )
        logger.info(f"Call connected: {participant}")
    except Exception as e:
        logger.error(f"Failed to place call: {e}")
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "book_appointment"
    asyncio.run(make_call(scenario))