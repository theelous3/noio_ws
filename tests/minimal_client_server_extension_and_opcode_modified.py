'''
This file outlays the basic requirements for creating a
websocket client and a websocket server, dealing strictly with
the websocket frame side of the protocol. This means, that it
does not detail the use of the opening handshake utilities.

It also gives an example of:
    1. Setting up a custom extension (deflate compression).
        * This involves setting the first reserved bit to 1
        and running the compression algorithim on the message
        payload before it is sent.

    2. Adding one custom message type opcode "latin_1".
    3. Adding one custom control type opcode "compare".

Note: We will use our deflate extension on all frames of type "latin_1".
'''

import noio_ws as ws
from noio_ws import utils

from zlib import compress, decompress


class WsClient:

    def __init__(self, opcode_type_mod={'latin_1': 3},
                 opcode_control_mod={'compare': 11}):

        self.sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.wsconn = ws.Connection(
            role='CLIENT',
            opcode_type_mod=opcode_type_mod,
            opcode_control_mod=opcode_control_mod)
        # A note on what we just did here:
        # The two modification args take a dictionary of
        # {type_name: type_number}. For non-control frames, the numbers
        # 3 - 7 inclusive are available.
        # For control frames the numbers 11 - 15 inclusive are available.
        # We can pass as many of these as there is space available in the
        # opcode designations.

    def main(self, location):
        self.sock.connect(location)

        # call util to do http side handshake
        # call util to verify response

        # spawn a task for sending messages

        self.incoming_message_manager()
        # spawn a task for incoming messages

    def incoming_message_manager():
        event = self.next_event()
        if event.type == 'text':
            ...
            # display the message or whatever
        elif event.type == 'binary':
            ...
            # do some binary-ish shit
        elif event.type == 'latin_1':
            event.message = decompress(event.message)
            ...
            # do some shit with our latin_1 message after
            # we decompress it.
        elif event.type == 'ping':
            ...
            # send the pong, like:
            # self.send(event.message, 'pong')
        elif event.type == 'pong':
            ...
            # confirmed, connection isn't pointless :)
        elif event.type == 'close':
            ...
            # feel free to get the status code or w/e
            # then send your side of the close:
            # self.send('', 'close')
            # at this point, we can exit the client.
        elif event.type == 'compare':
            ...
            # do whatever it is we want compare to do

    def send(self, message, type, fin=True, status_code=None):
        # here we check if we're sending our custom 'latin_1'
        # message type, and add deflate compression to it by compressing
        # the payload and turning the first reserved bit on.
        if type == 'latin_1':
            self.sock.sendall(
                wscon.send(
                    ws.Data(
                        compress(message), type, fin, status_code, rsv_1=1)))
        else:
            self.sock.sendall(
                wscon.send(ws.Data(message, type, fin, status_code)))

    def next_event(self):
        while True:
            event = self.wsconn.next_event()
            if event is ws.Information.NEED_DATA:
                self.wsconn.recv(self.sock.recv(2048))
                continue
            return event


websock_client = WsClient()
websock_client.main(('some_location.com', 80))


class WsServer:

    def __init__(self):
        self.sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def main(self, location):
        self.sock.bind(location)
        self.sock.listen(5)

        while True:
            client_sock, addr = self.sock.accept()
            # Here we spawn something to handle a connected client,
            # like an async task or threaded handler.
            handler = WsClientHandler(
                client_sock, addr, {'latin_1': 3}, {'compare': 11})
            handler.main()


class WsClientHandler:
    def __init__(self, sock, addr, opcode_type_mod,
                 opcode_control_mod):
        self.sock = sock
        self.addr = addr

        self.wsconn = ws.Connection(
            role='SERVER',
            opcode_type_mod=opcode_type_mod,
            opcode_control_mod=opcode_control_mod)

    def main(self):
        # - wait for client to send opening part of handshake
        # - call util to do verify request
        # - call util to respond to request
        # presuming everything is ok, we can begin doing
        # whatever it is our server does

        # here we'll just call the message manager
        self.incoming_message_manager()

    def incoming_message_manager():
        # This method is identical for both client and server :)
        event = self.next_event()
        if event.type == 'text':
            ...
            # display the message or whatever
        elif event.type == 'binary':
            ...
            # do some binary-ish shit
        elif event.type == 'latin_1':
            event.message = decompress(event.message)
            ...
            # do some shit with our latin_1 message after
            # we decompress it.
        elif event.type == 'ping':
            ...
            # send the pong, like:
            # self.send(event.message, 'pong')
        elif event.type == 'pong':
            ...
            # confirmed, connection isn't pointless :)
        elif event.type == 'close':
            ...
            # feel free to get the status code or w/e
            # then send your side of the close:
            # self.send('', 'close')
            # at this point, we can exit the client.
        elif event.type == 'compare':
            ...
            # do whatever it is we want compare to do

    def send(self, message, type, fin=True, status_code=None):
        # here we check if we're sending our custom 'latin_1'
        # message type, and add deflate compression to it by compressing
        # the payload and turning the first reserved bit on.

        # As you can see, this is also identical for both client and server :D
        if type == 'latin_1':
            self.sock.sendall(
                wscon.send(
                    ws.Data(
                        compress(message), type, fin, status_code, rsv_1=1)))
        else:
            self.sock.sendall(
                wscon.send(ws.Data(message, type, fin, status_code)))

    def next_event(self):
        while True:
            event = self.wsconn.next_event()
            if event is ws.Information.NEED_DATA:
                self.wsconn.recv(self.sock.recv(2048))
                continue
            return event


websock_server = WsServer()
websock_server.main(('some_location.com', 80))
