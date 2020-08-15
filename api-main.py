import websockets
import asyncio

import json
import time
from datetime import datetime
import threading

import a2s

import logging
logging.basicConfig(filename='example.log',level=logging.DEBUG)

from api_serverhandling import InitGameServers, Server

class GameCoordinator_Exception(BaseException):
    pass

class GameCoordinator_API:
    #The Game Coordinator API. This will handle searching for servers, processing lobbies and sending
    #clients information about the best server to join.
    thread = None
    serverList = {}

    connections = {}

    #Initalises the Game Coordinator API.
    def __init__(self):
        #Create server.
        print("Creating Game Coordinator Server.")

        print("Initalizing servers...")
        self.serverList = InitGameServers()
        
        #Create the searching thread.
        self.thread = threading.Thread(target=self.GCAPI_ServerSearch)
        self.thread.start()

        #Create event loop.
        print("Starting server...")
        server = websockets.serve(self.GCAPI_MessageHandler, "localhost", 8765)
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
                    connectorInfo[1] = datetime.now()   #Reset check time to now.
                    connectorInfo[2] = None             #Reset check time to nothing.

                #We haven't gone over the 1 minute reset check.
                #If we go over 30 connections with this IP, close.
                if connectorInfo[0] >= 30:
                    print(f"[API] {connector} is now being rate limited. > 30 connections between {connectorInfo[1]} -> {connectorInfo[2]}. Total connecton attempts: {connectorInfo[0]}.")
                    continue
            #If we don't have something already in our dict, add it.
            else:
                startT = datetime.now()
                self.connections[connector] = [1, startT, None] #Message count, the current time, a placeholder value for the check time.

            print(f"[API] Raw message received:\n{message}")

            #Decode this message into JSON.
            jsonObj = json.loads(message)

            #Whats our command?
            command = jsonObj["command"]
            
            #Run the command function here.
            if command != None:
                result = await self.commands[command](self, websocket, jsonObj)
                await websocket.send(result)

            #Not a valid command!
            else:
                raise GameCoordinator_Exception("Command not recognized.")
                self.GCAPI_HandleInvalidCommand(websocket, command)
    
    #Handles an invalid command.
    async def GCAPI_HandleInvalidCommand(self, websocket, commandsent):
        message = {
            "sender": "GCAPI",
            "commandrecv": commandsent,
            "message": "Invalid command.",
            "code": 404,
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

    async def GCAPI_FindServerCommand(self, websocket, jsonObj):
        sender = jsonObj["sender"]
        print(f"[API] Find server command activated by: {sender}")

        try:
            #Dict of all the information we need of this lobby.
            findinformation = jsonObj["find_information"]

            #Assemble:
            provider = findinformation["provider"]
            region = findinformation["region"]
            players = int(findinformation["players"])
            gamemode_list = findinformation["gamemodes"]
        except KeyError:
            message = {
                "sender": "GCAPI",
                "commandrecv": "find",
                "message": "Invalid paramaters.",
                "code": 404,
            }

            #Send.
            print(f"[API - FIND] Invalid parameters loaded.")
            return json.dumps(message, indent=4)

        #Print information.
        print("[API - FIND]")
        print("="*25)
        print(f"{sender} Lobby information:")
        print(f"Provider: {provider}")
        print(f"Search Region: {region}")
        print(f"Players in Lobby: {players}")
        print(f"List of Gamemodes: {gamemode_list}")
        print("="*25)

        #Error Checking:
        #Is this a valid provider?
        if self.serverList.get(provider) == None:
            message = {
                "sender": "GCAPI",
                "commandrecv": "find",
                "message": f"Invalid paramater value: {provider}",
                "code": 404,
            }

            #Send.
            return json.dumps(message, indent=4)
            
        print(f"[API - FIND] Valid provider: {provider}")

        #Do we have any gamemodes or maps?
        if len(gamemode_list) <= 0:
            message = {
                "sender": "GCAPI",
                "commandrecv": "find",
                "message": "Invalid paramaters. No maps or gamemodes.",
                "code": 404,
            }

            #Send.
            return json.dumps(message, indent=4)

        print("[API - FIND] Gamemodes and Maps are valid.")

        #Okay, we're all good. Let's get going.
        provider_serverlist = self.serverList[provider]
        bestServer = Server() #Load a blank object for easy manipulation.

        #Go through each server.
        for server in provider_serverlist:
            #Compare regions.
            if server.ServerRegion != region: #Regions are not equal.
                continue
            
            #Playercount check.
            if server.ServerPlayers == server.ServerMaxPlayers: #The server is full.
                continue
            
            #Go through each gamemode in the gamemode list and see if it's one we want.
            acceptableGameMode = False

            for gamemode in gamemode_list:
                if gamemode == "":
                    acceptableGameMode = True
                    break

                if server.ServerGameMode in gamemode: #Is this gamemode name contained in the server gamemode string?
                    acceptableGameMode = True
                    break
            
            if acceptableGameMode == False: #Couldn't find a gamemode.
                continue
            
            #We've passed all of these checks so this server is possibly good, is it the one with the most players though?
            if server.ServerPlayers > bestServer.ServerPlayers:
                bestServer = server
        
        print(f"[API] Best server!: {bestServer}, {bestServer.ServerPlayers}/{bestServer.ServerMaxPlayers}, {bestServer.ServerMap}")

        message = {
           "sender": "GCAPI",
           "commandrecv": "find",
           
           "find_information":
           {
                "provider": bestServer.ServerProviderName,
                "servername": bestServer.ServerName,
                "serverip": bestServer.ServerIP,
                "serverport": bestServer.ServerPort,
                "region": bestServer.ServerRegion,
                "players": bestServer.ServerPlayers,
                "maxplayers": bestServer.ServerMaxPlayers,
                "map": bestServer.ServerMap,
                "gamemode": bestServer.ServerGameMode,
           },

           "code": 200,
        }

        #Send.
        return json.dumps(message, indent=4)

    #Main loop that handles searching for servers.
    def GCAPI_ServerSearch(self):
        while True:
            try:
                #Go through each provider..
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
GameCoordinator = GameCoordinator_API()