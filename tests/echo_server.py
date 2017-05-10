import h11
import curio
from curio import socket

import noio_ws as ws
from noio_ws import utils
from noio_ws.errors import NnwsProtocolError

httpcon = h11.Connection(our_role=h11.SERVER)  # our h11 http connection
wscon = ws.Connection('SERVER')  # our noio_ws websocket connection


async def client_handler(connection, addr):
    print(f'Connection from {addr}')
    ws_shaker = utils.Handshake('SERVER')
    request = await http_next_event(connection)
    request = ws_shaker.verify_request(request)
    await http_send(
        connection, ws_shaker.server_handshake())
    while True:
        event = await ws_next_event(connection)
        print('got ws message', vars(event))
        if isinstance(event, ws.Message):
            if event.type != 'close':
                print(f'{event.message} from {addr}')
                await ws_send(connection, event.message, event.type)
                await ws_send(connection, '', 'close')
            else:
                print(event.type)
                print('WE EXITED CLEANLY...ISH')
                raise SystemExit


async def main(location):
    print('Server started')
    sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(location)
    sock.listen(5)
    while True:
        connection, addr = await sock.accept()
        await curio.spawn(client_handler(connection, addr))


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
            if not stuff:
                print('no stuff')
                raise SystemExit
            wscon.recv(stuff)
            continue
        return event

curio.run(main(('localhost', 25000)))
