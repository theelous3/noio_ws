import noio_ws as ws
import curio
from curio import socket


class WSServerHandler:
    def __init__(self, server, sock, addr):
        self.server = server
        self.sock = sock
        self.addr = addr
        self.wcon = ws.Connection(role='SERVER', host='lol')

    async def main(self):
        await self.send(('Chat', 'Server'), f'Welcome {self.addr}')
        while True:
            event = await self.get_event()
            if isinstance(event, ws.Message):
                for client, handler in self.server.connections.items():
                    await handler.send(self.addr, event.message)

    async def get_event(self):
        while True:
            event = self.wcon.next_event()
            if event is ws.Directive.NEED_DATA:
                self.wcon.recv((await self.sock.recv(4096)))
                continue
            return event

    async def send(self, sender, message):
        await self.sock.sendall(
            self.wcon.send(
                ws.Data('|'.join(map(str, sender)) + ': ' + message, 'text', True)))


class WsServer:
    def __init__(self):
        self.connections = {}

    async def main(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('localhost', 25000))
        sock.listen(5)
        print('Server started')
        while True:
            connection, client = await sock.accept()
            print(client, 'connected')
            client_handler = WSServerHandler(self, connection, client)
            self.connections[client] = client_handler
            await curio.spawn(client_handler.main())

if __name__ == '__main__':
    server = WsServer()
    curio.run(server.main())
