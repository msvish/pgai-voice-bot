import asyncio
import logging
import os

from dotenv import load_dotenv
from livekit import api

load_dotenv()

logger = logging.getLogger("make-call")
logger.setLevel(logging.INFO)

room_name = "pgai-test-call"
agent_name = "pgai-caller"
outbound_trunk_id = os.environ["SIP_OUTBOUND_TRUNK_ID"]


async def make_call(phone_number: str):
    lkapi = api.LiveKitAPI()

    logger.info(f"Dispatching agent {agent_name} to room {room_name}")
    await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(agent_name=agent_name, room=room_name)
    )

    logger.info(f"Dialing {phone_number} into {room_name}")
    try:
        participant = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                sip_number="+15822335108",  # add this line
                room_name=room_name,
                participant_identity="pgai-test-line",
                participant_name="PGAI Test Line",
                wait_until_answered=True,
            )
        )
        logger.info(f"Call connected: {participant}")
    except Exception as e:
        logger.error(f"Failed to place call: {e}")
    finally:
        await lkapi.aclose()


async def main():
    await make_call("+18054398008")


if __name__ == "__main__":
    asyncio.run(main())