import asyncio
import websockets

async def hello(websocket, path):
    msg = await websocket.recv()
    print("< {}".format(msg))

    greeting = "{}".format(msg)
    await websocket.send(greeting)
    print("> {}".format(greeting))
    print(len(msg))

start_server = websockets.serve(hello, 'localhost', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
