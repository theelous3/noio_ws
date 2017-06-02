import h11
import curio
from curio import socket

import noio_ws as ws
from noio_ws.handshake_utils import Handshake
from noio_ws.errors import NnwsProtocolError

from random import choice
from string import ascii_lowercase


TEXT_TO_GO = ''.join([choice(ascii_lowercase) for _ in range(200)])


class WsClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.http_conn = h11.Connection(our_role=h11.CLIENT)
        self.ws_shaker = Handshake('CLIENT')

        self.ws_conn = ws.Connection('CLIENT')

    async def main(self, location):
        await self.sock.connect(location)

        shake_data = self.ws_shaker.client_handshake('ws://echo.websocket.org')
        await self.http_send(shake_data, h11.EndOfMessage())
        http_response = await self.http_next_event()
        self.ws_shaker.verify_response(http_response)

        # Handshake done. Now to websocket stuff!
        await self.ws_send(TEXT_TO_GO, 'text')
        incoming_messages_task = await curio.spawn(
            self.incoming_message_manager)
        await incoming_messages_task.join()

    async def incoming_message_manager(self):
        while True:
            event = await self.ws_next_event()
            if event.type == 'text':
                print(event.message)
                await self.ws_send('', 'close')
            elif event.type == 'binary':
                pass
                # do some binary-ish things
            elif event.type == 'ping':
                await self.ws_send(event.message, 'pong')
            elif event.type == 'pong':
                pass
            elif event.type == 'close':
                return

    async def ws_send(self, message, type, fin=True, status_code=None):
        await self.sock.sendall(
            self.ws_conn.send(ws.Data(message, type, fin, status_code)))

    async def ws_next_event(self):
        while True:
            event = self.ws_conn.next_event()
            if event is ws.Information.NEED_DATA:
                self.ws_conn.recv(await self.sock.recv(2048))
                continue
            return event

    async def http_send(self, *events):
        for event in events:
            data = self.http_conn.send(event)
            if data is not None:
                await self.sock.sendall(data)

    async def http_next_event(self):
        while True:
            event = self.http_conn.next_event()
            if event is h11.NEED_DATA:
                self.http_conn.receive_data(await self.sock.recv(2048))
                continue
            return event

client = WsClient()
curio.run(client.main(('echo.websocket.org', 80)))
