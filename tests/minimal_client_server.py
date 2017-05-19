'''
This file outlays the basic requirements for creating a
websocket client and a websocket server, dealing strictly with
the websocket frame side of the protocol. This means, that it
does not detail the use of the opening handshake utilities
nor does it deal with adding extensibility.
'''

import noio_ws as ws


class WsClient:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.ws_conn = ws.Connection(role='CLIENT')

    def main(self, location):
        self.sock.connect(location)

        # spawn a task for sending messages

        self.incoming_message_manager()
        # spawn a task for incoming messages

    def incoming_message_manager():
        while True:
            event = self.next_event()
            if event.type == 'text':
                ...
                # display the message or whatever
            elif event.type == 'binary':
                ...
                # do some binary-ish shit
            elif event.type == 'ping':
                ...
                # send the pong, like:
                # self.ws_send(event.message, 'pong')
            elif event.type == 'pong':
                ...
                # confirmed, connection isn't pointless :)
            elif event.type == 'close':
                ...
                # feel free to get the status code or w/e
                # then send your side of the close:
                # self.ws_send('', 'close')
                # at this point, we can exit the client.

    def ws_send(self, message, type, fin=True, status_code=None):
        self.sock.sendall(
            self.ws_conn.send(ws.Data(message, type, fin, status_code)))

    def next_event(self):
        while True:
            event = self.ws_conn.next_event()
            if event is ws.Information.NEED_DATA:
                self.ws_conn.recv(self.sock.recv(2048))
                continue
            return event


websock_client = WsClient()
websock_client.main(('some_location.com', 80))


class WsServer:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def main(self, location):
        self.sock.bind(location)
        self.sock.listen(5)

        while True:
            client_sock, addr = self.sock.accept()
            # Here we spawn something to handle a connected client,
            # like an async task or threaded handler.
            handler = WsClientHandler(client_sock, addr)
            handler.main()


class WsClientHandler:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr

        self.ws_conn = ws.Connection(role='SERVER')

    def main(self):
        # here we'll just spawn an x for the message manager
        self.incoming_message_manager()

    def incoming_message_manager():
        while True:
            event = self.next_event()
            elif event.type == 'text':
                ...
                # print the message or whatever
            elif event.type == 'binary':
                ...
                # do some binary-ish things
            elif event.type == 'ping':
                ...
                # send the pong, like:
                # self.ws_send(event.message, 'pong')
            elif event.type == 'pong':
                ...
                # confirmed, connection isn't pointless :)
            elif event.type == 'close':
                ...
                # feel free to get the status code or w/e
                # then send your side of the close:
                # self.ws_send('', 'close')
                # at this point, we can exit the client.

    def ws_send(self, message, type, fin=True, status_code=None):
        self.sock.sendall(
            ws_conn.send(ws.Data(message, type, fin, status_code)))

    def next_event(self):
        while True:
            event = self.ws_conn.next_event()
            if event is ws.Information.NEED_DATA:
                self.ws_conn.recv(self.sock.recv(2048))
                continue
            return event


websock_server = WsServer()
websock_server.main(('some_location.com', 80))
