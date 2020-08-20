import websockets
import asyncio

import json
import time
from datetime import datetime
import threading

import a2s
import logging
logging.basicConfig(filename='example.log',level=logging.DEBUG)

from api_serverhandling import InitGameServers, Server, listofProviders
from api_commands import GCAPI_FindServerCommand

class GameCoordinator_Exception(BaseException):
    pass

#The Game Coordinator API. This will handle searching for servers, processing lobbies and sending
#clients information about the best server to join.
class GameCoordinator_API:
    thread = None #Dedicated server searching thread.
    serverList = {} #{provider name (e.g "creators.tf"), server obj}
    connections = {} #{ip address, list}

    ratelimit_HookValue = 30 #By default, the value for rate limiting is 30.
    ipaddress = () #The IP and port used to connect.

    #Initalises the Game Coordinator API.
    def __init__(self, bindAddress):
        #Create server.
        print("Creating Game Coordinator Server.")

        print("Initalizing servers...")
        self.serverList = InitGameServers()
        
        #Create the searching thread.
        self.thread = threading.Thread(target=self.GCAPI_ServerSearch)
        self.thread.start()

        #Create the server.
        self.ipaddress = bindAddress
        print(f"Starting server... Binding to: {self.ipaddress}")

        server = websockets.serve(self.GCAPI_MessageHandler, self.ipaddress[0], self.ipaddress[1])
        asyncio.get_event_loop().run_until_complete(server)
        asyncio.get_event_loop().run_forever()
    
    #The main message receiving loop.
    async def GCAPI_MessageHandler(self, websocket, path):
        #Receives a message from the client.
        async for message in websocket:
            connector = websocket.remote_address[0] #Grab IP Address.
            print(f"[API] Connection made. {connector}")

            #Rate limit checking:
            if self.connections.get(connector) != None:
                #Grab connection info for this IP which is stored in a dict with the following: 
                #<IP>: [<connection attempts (int)>, <time of first connection within a minute>, <the time that is compared, usually None>]
                connectorInfo = self.connections[connector] 

                connectorInfo[0] += 1 #Up our connection count.
                connectorInfo[2] = datetime.now() #Get the current time and set it as our check time.
                
                #Compare times here:
                finalTime = connectorInfo[2] - connectorInfo[1] #Subtract the first time from the check time.
                if finalTime.seconds/60 >= 1: #Over 1 minute?
                    connectorInfo[0] = 0                #Reset count to 0 to allow new messages.
                    connectorInfo[1] = datetime.now()   #Reset the first time to now.
                    connectorInfo[2] = None             #Reset check time to nothing.

                #We haven't gone over the 1 minute reset check.
                #If we go over X connections with this IP, close.
                if connectorInfo[0] >= self.ratelimit_HookValue:
                    #Send a message saying that you're being rate limited.
                    if connectorInfo[0] == self.ratelimit_HookValue:
                        message = {
                            "sender": "GCAPI",
                            "recv": message,
                            "message": f"Too many connections.",
                            "code": 400,
                        }

                        await websocket.send(json.dumps(message, indent=4))
                    print(f"[API] {connector} is now being rate limited. > {self.ratelimit_HookValue} connections between {connectorInfo[1]} -> {connectorInfo[2]}. Total connecton attempts: {connectorInfo[0]}.")
                    await websocket.close()

                    continue

            #If we don't have something already in our dict, add it.
            else:
                startT = datetime.now()
                self.connections[connector] = [1, startT, None] #Message count, the current time, a placeholder value for the check time.

            print(f"[API] Raw message received:\n{message}")

            try:
                #Decode this message into JSON.
                jsonObj = json.loads(message)
            except JSONDecodeError:
                print(f"[API] Invalid message received.")
                message = {
                    "sender": "GCAPI",
                    "recv": message,
                    "message": "Invalid syntax.",
                    "code": 400,
                }
                await websocket.send(json.dumps(message, indent=4))

                #Close this connection.
                await websocket.close()
                continue

            #Whats our command?
            command = jsonObj["command"]
            
            #Run the command function here.
            if command != None:
                result = await self.commands[command](self, websocket, jsonObj)
                await websocket.send(result)

            #Not a valid command!
            else:
                self.GCAPI_HandleInvalidCommand(websocket, command)

            #Close this connection.
            await websocket.close()
    
    #Handles an invalid command.
    async def GCAPI_HandleInvalidCommand(self, websocket, commandsent):
        message = {
            "sender": "GCAPI",
            "commandrecv": commandsent,
            "message": "Invalid command.",
            "code": 400,
        }

        #Send.
        return json.dumps(message, indent=4)

    #Heartbeat command.
    async def GCAPI_HeartbeatCommand(self, websocket, jsonObj):
        message = {
            "sender": "GCAPI",
            "commandrecv": "heartbeat",
            "message": "Game Coordinator API is online.",
            "code": 200,
        }

        #Send.
        return json.dumps(message, indent=4)


    #Main loop that handles searching for servers.
    def GCAPI_ServerSearch(self):
        while True:
            try:
                for provider in self.serverList:
                    provider_serverlist = self.serverList[provider]

                    #Go through each server.
                    for server in provider_serverlist:
                        #Ping with A2S.
                        a2s_server = a2s.info((server.ServerIP, server.ServerPort), timeout = 2)

                        #Change information.
                        server.ServerName = a2s_server.server_name
                        server.ServerMap = a2s_server.map_name
                        server.ServerPlayers = a2s_server.player_count

                        gameModeTemp = server.ServerMap.split("_")
                        server.ServerGameMode = gameModeTemp[0]

                        #print(f"[SERVER SEARCH - GOOD] Name: {server.ServerName}, Map: {server.ServerMap}, Players: {server.ServerPlayers}/{server.ServerMaxPlayers}")
            except BaseException as exception:
                #print(f"[SERVER SEARCH - FAIL] Failed to connect to server: {server.ServerIP}:{server.ServerPort}. Reasoning: {exception}")
                server.ServerName = ""
                server.ServerMap = ""
                server.ServerPlayers = -1

    commands = {
        "heartbeat": GCAPI_HeartbeatCommand,
        "find": GCAPI_FindServerCommand,
    }
        

#Create the class.
GameCoordinator = GameCoordinator_API(("localhost", 8765))