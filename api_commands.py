import json
import asyncio
import a2s
from api_serverhandling import listofProviders, Server

class GC_Commands_Exception(BaseException):
    pass

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
            "code": 400,
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
    validProvider = False

    for providerObj in listofProviders:
        if provider in providerObj.Provider_UseNames:
            validProvider = True

            #To make sure we can read from our dict properly, we change the name of this to the one set in the Provider obj.
            provider = providerObj.ProviderName
            break
    
    if validProvider == False:
        message = {
            "sender": "GCAPI",
            "commandrecv": "find",
            "message": f"Invalid paramater value: {provider}",
            "code": 400,
        }

        #Send.
        return json.dumps(message, indent=4)
    #----------------------------------------------------------------------

    print(f"[API - FIND] Valid provider: {provider}")

    #Do we have any gamemodes or maps?
    if len(gamemode_list) <= 0:
        message = {
            "sender": "GCAPI",
            "commandrecv": "find",
            "message": "Invalid paramaters. No maps or gamemodes.",
            "code": 400,
        }

        #Send.
        return json.dumps(message, indent=4)

    print("[API - FIND] Gamemodes are valid.")

    #Okay, we're all good. Let's get going.
    provider_serverlist = self.serverList[provider]
    bestServer = Server() #Load a blank object for easy manipulation.

    while True:
        print("[API - FIND] Server checking...")

        #Go through each server.
        for server in provider_serverlist:
            #Compare regions.
            if server.ServerRegion != region: #Regions are not equal.
                continue
            
            #Playercount check.
            if server.ServerPlayers == server.ServerMaxPlayers: #The server is full.
                continue
            
            #Is this gamemode name contained in the server gamemode string?
            if server.ServerGameMode not in gamemode_list:
                continue

            #We've passed all of these checks so this server is possibly good, is it the one with the most players though?
            if server.ServerPlayers > bestServer.ServerPlayers:
                bestServer = server

        print("[API - FIND] Server checking complete. Attempting check on best server.")

        try:
            a2s_server = a2s.info((bestServer.ServerIP, bestServer.ServerPort), timeout = 2)

            #Change information.
            bestServer.ServerName = a2s_server.server_name
            bestServer.ServerMap = a2s_server.map_name
            bestServer.ServerPlayers = a2s_server.player_count

            gameModeTemp = bestServer.ServerMap.split("_")
            bestServer.ServerGameMode = gameModeTemp[0]

            #Is the server full?
            if bestServer.ServerPlayers == bestServer.ServerMaxPlayers:
                raise GC_Commands_Exception("Server is full.")

            #Is the gamemode acceptable?
            if bestServer.ServerGameMode not in gamemode_list:
                raise GC_Commands_Exception("Server gamemode type has changed from the one requested.") 

            break #Exit while loop.
        except BaseException as exception:
            print(f"[API - FIND] Best server check failure: {exception}")
            continue

    print(f"[API - FIND] Best server!: {bestServer}, {bestServer.ServerPlayers}/{bestServer.ServerMaxPlayers}, {bestServer.ServerMap}")

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