Extension and new opcode example
================================

In the previous section we took a look at a client and server that use the base opcodes, default reserved bits, and did nothin' fancy. Here we will write a similar example, adding a custom control frame, non-control frame, and implement a basic compression extension.

As before we'll begin by instancing our ``Connection`` object, though we'll pass some extra arguments. ::

    import noio_ws as ws

    from zlib import compress, decompress
    import time

    # We'll add a new control frame that sends the current unix time when requested.
    new_control_frame = {'time': 11}
    # We'll add a new non-control frame to indicate our message is ascii compatible.
    new_non_control_frame = {'ascii', 3}

    ws_conn = ws.Connection('CLIENT',
                            opcode_non_control_mod=new_non_control_frame,
                            opcode_control_mod=new_control_frame)
    # Bam! We've started our connection and registered the new frame types.

For our compression extension, we'll be using the first reserved bit to indicate if a message is compressed or not. We'll add a check for the reserved bit in our inbound-stuff function and decompress as required. ::

    def incoming_message_manager():
        while True:
            event = ws_next_event()

            # here we check for compression, and decompress if needed
            # adding extensions is easy!
            if event.reserved[0] is 1:
                event.message = decompress(event.message)

            if event.type == 'text':
                ...
                # print the message or whatever
            elif event.type == 'binary':
                ...
                # do some binary-ish things
            elif event.type == 'ping':
                ...
                # send the pong, like:
                # ws_send(event.message, 'pong')
            elif event.type == 'pong':
                ...
                # confirmed, connection isn't pointless :)
            elif event.type == 'close':
                ...
                # feel free to get the status code or w/e
                # then send your side of the close:
                # ws_send('', 'close')
                # at this point, we can exit the client.
            elif event.type == 'time':
                ws_send(''.format(time.time()), 'text')

That covers our two new opcodes and extension for incoming frames, but what about outgoing frames? We'll modify the basic ``ws_send()`` from the basic examples to handle that for us. ::

    def ws_send(message, type, fin=True, status_code=None, deflate=False):
        rsv_1 = 0
        if deflate:
            message = compress(message)
            rsv_1 = 1
        sock.sendall(
            ws_conn.send(ws.Data(message, type, fin, status_code, rsv_1=rsv_1)))

And that's it. Everything else remains the same. You can add extensions and opcodes as arbitrarily as you like.

There is no difference between client and server for extending the protocol like this.

Here's the new client example in full: ::

    import noio_ws as ws
    import socket

    import time
    from zlib import compress, decompress

    class WsClient:

        def __init__(self):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self.ws_conn = ws.Connection(
                'CLIENT',
                opcode_non_control_mod={'ascii', 3},
                opcode_control_mod={'time': 11})

        def main(self, location):
            self.sock.connect(location)

            # spawn an x to control sending messages

            # spawn an x to control incoming messages
            self.incoming_message_manager()

        def incoming_message_manager():
            while True:
                event = ws_next_event()

                # here we check for compression, and decompress if needed
                # adding extensions is easy!
                if event.reserved[0] is 1:
                    event.message = decompress(event.message)

                if event.type == 'text':
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
                elif event.type == 'time':
                    self.ws_send(''.format(time.time()), 'text')

        def ws_send(self, message, type, fin=True, status_code=None, deflate=False):
        rsv_1 = 0
        if deflate:
            message = compress(message)
            rsv_1 = 1
        self.sock.sendall(
            self.ws_conn.send(ws.Data(message, type, fin, status_code, rsv_1=rsv_1)))

        def ws_next_event(self):
            while True:
                event = self.ws_conn.next_event()
                if event is ws.Information.NEED_DATA:
                    self.ws_conn.recv(self.sock.recv(2048))
                    continue
                return event


    websock_client = WsClient()
    websock_client.main(('some_location.com', 80))
