# Game-Coordinator-API
A Game Coordinator API service for TF2 Community Servers.

## Installation and Usage:

1. Install the latest version of Python. (Tested with Python 3.8)
2. Install the [A2S module](https://pypi.org/project/python-a2s/) with 
```pip3 install python-a2s```

3. Configure the */cfg/providers.json* file. This file contains all of the information that is required to add a provier to the Game Coordinator. The format is as follows:
```
{
    "<main_provider_name>": 
    {
        "url": "<url here. e.g provider.tf/api/serverList/>",
        "enabled": true (or false),

        "names": [
            <a list of names that can be used with this provider e.g:>
            "provider", "provider.tf"
        ],

        "regions": [
            <a list of regions that can be used with this provider. try and stick to the same format:>
            "us", "eu", "ru", "au", "sg"
        ]
    },
}
```
3. Run *api-main.py*. By default, it binds to *localhost:8765*. This can be changed on line 41:
```python
server = websockets.serve(self.GCAPI_MessageHandler, "localhost", 8765)
```

## Connecting to the API:
Included is an example file: *client_example.py*. This file provides a basic example for connecting to the API, sending a JSON message with the *find* command, and printing out the result that comes back from the API. The API uses Websockets for connecting and sending messages.

A basic connection example using Python and Websockets is as follows:
```python
import asyncio
import websockets

url = "ws://localhost:8765"
   async with websockets.connect(url) as websocket:
```

### Rate Limiting.
Rate-Limiting is also built into the main application. Each IP-Address can only send 30 messages per minute. Clients will be automatically disconnected without a response if they exceed this limit. This can be changed on line 70:
```python
...
if connectorInfo[0] >= 30: #30 messages per minute.
...
```

### Sending Messages.
The main form of sending, decoding, and receiving messages using the API is via JSON. Sending a server find command is as easy as follows:

```json
{
  "sender": "ClientExample",
  "command": "find",

  "find_information": {
    "provider": "provider.tf",
    "region": "eu",
    "players": "1",
    "gamemodes": ["pl", "koth"],
  }
}
```

This is a message you could possibly get back:

```json
{
    "sender": "GCAPI",
    "commandrecv": "find",
    "find_information": {
        "provider": "provider.tf",
        "servername": "Provider.TF | Europe #1",
        "serverip": "123.456.789.000",
        "serverport": 27015,
        "region": "eu",
        "players": 22,
        "maxplayers": 24,
        "map": "pl_upward",
        "gamemode": "pl"
    },
    "code": 200
}```
