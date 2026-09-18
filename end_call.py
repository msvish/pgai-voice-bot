import asyncio
import sys

from livekit import api


async def main(room_name: str):
    lkapi = api.LiveKitAPI()
    await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
    await lkapi.aclose()
    print(f"Deleted room: {room_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python end_call.py <room_name>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))