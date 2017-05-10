'''
import noio_ws.constants
from noio_ws.noio_ws import Data, Recvr

data = Data('hello ', 'text', True)
data = data()
data_c = Data('PING BODY', 'ping', True)
data_c = data_c()
data2 = Data('world', 'continuation', True)
data2 = data2()
rvr = Recvr()
r = rvr(data[0])
vars(r)
r = rvr(data_c[0])
vars(r)
r = rvr(data2[0])
vars(r)


# ez test
import noio_ws as ws

wcon_c = ws.Connection(role='CLIENT', opcode_type_mod={'wang-jangle': 3})
a = wcon_c.send(ws.Data('HELLO serveadwaadwaddwwdr', 'wang-jangle', True))


wcon_s = ws.Connection(role='SERVER', opcode_type_mod={'wang-jangle': 3})
wcon_s.recv(a)
b = wcon_s.next_event()
print(b.message)
'''

# Bare WS Client Side API

import noio_ws as ws
from noio_ws import utils


class WsClient:

    def __init__(self, opcode_control_mod):
        self.sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.wsconn = ws.Connection(
            role='CLIENT', opcode_control_mod=opcode_control_mod)

    def main(self, location):
        self.sock.connect(location)

        # call util to do http side handshake
        # call util to verify response

        # spawn a task for sending messages

        self.incoming_message_manager()
        # spawn a task for incoming messages

    def incoming_message_manager():
        event = self.next_event()
        if event is ws.Information.NEED_DATA:
            ...
            # there is no event
        elif event.type == 'text':
            ...
            # display the message or whatever
        elif event.type == 'binary':
            ...
            # do some binary-ish shit
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
        elif event.type == 'wang-jangle':
            ...
            # do some shit with our custom opcode

    def send(self, message, type, fin=True, status_code=None):
        self.sock.sendall(
            wscon.send(ws.Data(message, type, fin, status_code)))

    def next_event(self):
        while True:
            event = self.wsconn.next_event()
            if event is ws.Information.NEED_DATA:
                self.wsconn.recv(self.sock.recv(2048))
                continue
            return event


websock_client = WsClient({'wang-jangle': 3})
websock_client.main(('some_location.com', 80))
