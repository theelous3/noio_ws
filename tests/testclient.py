from collections import deque
from Tkinter import *

import curio
from curio import socket

import asks
import h11

import noio_ws as ws


class WSClient:
    def __init__(self):
        self.wcon = ws.Connection(role='CLIENT')

    async def main(self):
        self.sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        await self.sock.connect(('localhost', 25000))
        while True:
            await self.ws_get_event()
            message = input('>')
            await self.ws_send(message)

    async def ws_get_event(self):
        while True:
            event = self.wcon.next_event()
            if event is ws.Directive.NEED_DATA:
                self.wcon.recv((await self.sock.recv(4096)))
                continue
            print(event.message)

    async def ws_send(self, message):
        await self.sock.sendall(self.wcon.send(ws.Data(message, 'text', True)))


'''
wcon = ws.Connection(role='CLIENT', extensions=['a', 'b'], subprotocols=['c', 'd'])
ws_shake = ws.Handshake(wcon)
print(wcon.next_event())
>>> SEND HANDSHAKE
hconn.send(ws_shake.client_handshake(uri))
resp = get_server_response()
ws_shake.verify_response(resp)
if we_are_happy_with_the_response:
    wcon.send(Directive.ACCEPT_CONNECTION)

wcon = ws.Connection(role='SERVER', extensions=['a', 'b'], subprotocols=['c', 'd'])
ws_shake = ws.Handshake(wcon)
print(wcon.next_event())
>>> NEED DATA
hconn.recv(from_socket))
resp = get_client_reqquest()
ws_shake.verify_request(req)
hconn.send(ws_shake.server_handshake({'some': 'shit'}))
wcon.send(Directive.ACCEPT_CONNECTION)





print(wcon.send(Handshake(
    'http://www.iana.org/domains/example/', protocols='theelous3.net/chat', extensions='gzip')))
print(wcon.next_event())
print(wcon.nonce)
wcon.recv(b'HTTP/1.0 302 Found\r\nLocation: http://www.iana.org/domains/example/\r\nServer: BigIP\r\nConnection: Keep-Alive\r\nContent-Length: 0\r\n\r\n')
'''
