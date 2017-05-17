import noio_ws as ws
import curio
from curio import socket


class WSServerClientHandler:
    def __init__(self, server, sock, addr):
        self.server = server
        self.sock = sock
        self.addr = addr
        self.wcon = ws.Connection(role='SERVER', host='lol')

    async def main(self):
        await self.server_send(f'Welcome {self.addr}', 'text')
        while True:
            event = await self.get_event()
            print(event)
            if isinstance(event, ws.Message):
                if event.type == 'text':
                    for client, client_handler in self.server.connections.items():
                        await client_handler.send(self.addr, event.message, 'text')
            elif event == ws.Directive.SEND_CLOSE:
                await self.server_send('', 'close')
                del self.server.connections[self.addr]
                for client, client_handler in self.server.connections.items():
                    await client_handler.server_send(f'{self.addr} disconnected.', 'text')
                break
            await curio.sleep(0)

    async def get_event(self):
        while True:
            event = self.wcon.next_event()
            if event is ws.Directive.NEED_DATA:
                self.wcon.recv((await self.sock.recv(4096)))
                continue
            return event

    async def server_send(self, message, type):
        await self.sock.sendall(
            self.wcon.send(
                ws.Data('*'*5 + 'Chat|Server:' +
                        message, type, True)))

    async def send(self, sender, message, type):
        await self.sock.sendall(
            self.wcon.send(
                ws.Data('|'.join(map(str, sender)) + ': ' +
                        message, type, True)))


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
            client_handler = WSServerClientHandler(self, connection, client)
            self.connections[client] = client_handler
            await curio.spawn(client_handler.main())
            print('awaiting new client')

if __name__ == '__main__':
    server = WsServer()
    curio.run(server.main())
