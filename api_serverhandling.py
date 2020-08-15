import requests
import json
import os

class GC_Server_Exception(BaseException):
    pass

class Server:
    #Hardcoded values, should NOT be changed at runtime.
    ServerIP = ""
    ServerPort = -1
    ServerRegion = ""
    ServerMaxPlayers = -1
    ServerProviderName = ""

    #Feel free to touch these.
    ServerName = ""
    ServerMap = ""
    ServerPlayers = -1
    ServerGameMode = ""

    def __repr__(self):
        return f"{self.ServerIP}:{self.ServerPort}"

    #def __str__(self):
    #    return f"{self.ServerIP}:{self.ServerPort}"

#For the game coordinator to load servers into it's server-list, a request is made to the proviers API asking for server information.
#Server hosts will submit a URL where a request can be made that gets information back in raw JSON.
#The following format is required, and an example of this is shown here: (Creators.TF API)
#{
#   "servers": 
#   [
#       {
#           "id":101,
#           "is_down":false,
#           "ip":"164.132.203.200", (Required)
#           "port":27015, (Required)
#           "region":"eu", (Required)
#           "map":"pl_upward",
#           "online":24,
#           "maxplayers":24, (Required)
#           "hostname":"Creators.TF | West EU (France) | #101",
#           "passworded":false,
#           "since_heartbeat":26,
#       },
#    ]
#}

class Provider:
    ProviderName = ""
    ProviderURL = ""
    Provider_UseNames = []
    Provider_Regions = []

#The providers that we get servers from.
listofProviders = []

#Creates our list of game servers to use in the GC.
#Returns a list of all game servers used in the GC.
def InitGameServers():
    directory = os.path.dirname(os.path.abspath(__file__)) + "/cfg/"

    if os.path.isfile(directory + "providers.json") == False:
        raise GC_Server_Exception("Required config file (/cfg/providers.json is missing.")
        return None

    with open(directory + "providers.json") as providerList:
        jsonObj = json.load(providerList)

        #Loop through all of the providers we have listed.
        for provider in jsonObj:
            provider_jsonObj = jsonObj[provider]
            print(provider_jsonObj)

            #Create our provider object.
            provider_ClassObj = Provider()

            #Init values.
            provider_ClassObj.ProviderName = provider
            provider_ClassObj.ProviderURL = provider_jsonObj["url"]
            provider_ClassObj.Provider_Regions = provider_jsonObj["regions"]
            provider_ClassObj.Provider_UseNames = provider_jsonObj["names"]

            listofProviders.append(provider_ClassObj)
            

    #The server list is split up by providers, and it provides a list of Server class objects.
    serverlist = {}
    serverCount = 0

    for provider in listofProviders:
        finalServerList = [] #The final list that contains all of the objects.
        
        #Get the JSON back:
        url = provider.ProviderURL

        gameserverListRequest = requests.get(url) #Request information.

        if gameserverListRequest.status_code != 200:
            print(f"Provider {provider.ProviderName}'s URL ({provider.ProviderURL}) returned a non 200 response.")
            continue

        gameserverListJSON = gameserverListRequest.json()
        gameserverList = gameserverListJSON["servers"] #Assemble it all into a list that we can parse.

        print(f"Retrieving servers for provider: {provider.ProviderName}")

        #Go through all of the servers.
        for server in gameserverList:
            serverCount += 1
            gameServer = Server()

            #Init values.
            gameServer.ServerIP = server["ip"]
            gameServer.ServerPort = server["port"]
            gameServer.ServerRegion = server["region"]
            gameServer.ServerMaxPlayers = server["maxplayers"]
            gameServer.ServerProviderName = provider.ProviderName

            finalServerList.append(gameServer) #Add to the final list.

        if serverlist.get(provider.ProviderName) != None:
            serverlist[provider.ProviderName] += finalServerList
        else:    
            serverlist[provider.ProviderName] = finalServerList #Add to the provider list.
    
    print(f"Server loading done. Servers: {serverCount}")
    return serverlist