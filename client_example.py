#Game Coordinator API.
#Client example that connects to the API and sends a heartbeat message.

import asyncio
import websockets
import json

async def hello():
   uri = "ws://localhost:8765"
   while True:
      async with websockets.connect(uri) as websocket:
         message = {
            "sender": "ClientExample",
            "command": "find",

            "find_information":
            {
               "provider": "creators",
               "region": "eu",
               "players": "1",
               "gamemodes": ["pl", "koth", "cp"],
            }
         }

         messageStr = json.dumps(message, indent=4)
         print(message)
         await websocket.send(messageStr)

         recv = await websocket.recv()
         print(recv)

asyncio.get_event_loop().run_until_complete(hello())