import h11
import curio
from curio import socket

import noio_ws as ws
from noio_ws import utils
from noio_ws.errors import NnwsProtocolError

httpcon = h11.Connection(our_role=h11.CLIENT)  # our h11 http connection
wscon = ws.Connection('CLIENT')  # our noio_ws websocket connection


async def main(location):
    sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    await sock.connect(location)

    ws_shaker = utils.Handshake('CLIENT')
    shake_data = ws_shaker.client_handshake('ws://localhost/chat')

    await http_send(sock, shake_data, h11.EndOfMessage())
    http_response = await http_next_event(sock)

    http_response = ws_shaker.verify_response(http_response)
    if isinstance(http_response, h11.Response):
        pass
        # In this case, the server responded with a status code
        # other than 101 and auth requests or something might need
        # to take place in the realm of the http protocol.

    # If we get this far, it means verification didn't throw a
    # NnwsProtocolError and the server upgraded our connection.
    # We can do real websocket stuff now.

    # Let's send a message to an echo server, wait for the response
    # and then close the connection.

    await ws_send(sock, 'Hello server!', 'text')

    while True:
        response = await ws_next_event(sock)
        if isinstance(response, ws.Message):
            print(f'Message recieved :D\n{response.message}')
            await ws_send(sock, '', 'close')
        elif response is ws.Information.CONNECTION_CLOSED:
            print('WE EXITED CLEANLY...ISH')
            raise SystemExit


async def http_send(sock, *events):
    for event in events:
        data = httpcon.send(event)
        if data is not None:
            await sock.sendall(data)


async def http_next_event(sock):
    while True:
        event = httpcon.next_event()
        if event is h11.NEED_DATA:
            httpcon.receive_data(await sock.recv(2048))
            continue
        return event


async def ws_send(sock, message, type, fin=True, status_code=None):
    await sock.sendall(wscon.send(ws.Data(message, type, fin, status_code)))


async def ws_next_event(sock):
    while True:
        event = wscon.next_event()
        if event is ws.Information.NEED_DATA:
            stuff = await sock.recv(2048)
            print(stuff)
            wscon.recv(stuff)
            continue
        return event

curio.run(main(('localhost', 25000)))


