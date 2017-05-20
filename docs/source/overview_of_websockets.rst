A brief overview of the websocket protocol
==========================================

Things you absolutely must know in order to write a websocket client or server
______________________________________________________________________________

The websocket protocol communicates with frames. Frames are a header + application data. The frame header contains information about the frame and the application data. The application data is any and all stuff you send in the frame "body".

In its most basic form the websocket protocol has three non-control frames and three control frames. These are

* Non-control:
   * 'text' - denotes we are sending 'utf-8' encoded bytes
   * 'binary' - denotes we are sending raw bytes
   * 'continue' - denotes this message is a continuation fragment of the previous message.
* Control:
   * 'close' - says we either want to close, or are responding to a close
   * 'ping' - pings!
   * 'pong' - pongs!

These frame types are denoted by ``ints`` in bit form stuffed halfway in to a byte in the frame. The int is called the opcode.

There is a ``fin`` bit, which denotes if the frame is the last in a series of one or more frames.

In order to send a utf-8 encoded 'hello world' we would use a ``text`` frame with the ``fin`` bit set to 1, signaling that this is the only frame in the series and the payload contains utf-8 encoded text.

In order to send 'hello ' as one frame, and 'world' as another, but keep them as part of the same series such that the receiver reads them as one message, we would send a 'text' frame with 'hello ' and the fin bit set to 0, and then a 'continue' frame of 'world' with the ``fin`` bit set to 1.

You can send control frames in the middle of a fragmented non-control frame, but you can't send non-control frames in the middle of a fragmented non-control frame.

You cannot fragment a control frame, and the control frames body must not be longer than 125 bytes.

There are three ``rsv`` (reserved) bits that may be set to 1, and by default are 0.

If you send or receive a ``close`` frame, any further stuff received that is not a ``close`` frame must be discarded. If you sent the ``close`` frame you must wait to receive one in turn, and then may end the connection, and vice-versa.

It is not required to understand everything on this page in order to effectively write a websocket client or server. However, if you're making something non-trivial you will probably want to be familiar with the stuff above, and general concepts like the structure of a websocket frame, opcodes, fin bit, rsrv bits, extension/subprotocol headers.

**Thus ends the 'things you absolutely must know' section.**

The websocket connection lifespan and frame structure.
______________________________________________________

Websockets have four states: ``connecting``, ``open``, ``closing`` and ``closed``. All communication between clients and servers takes place though the use of the websocket ``frame``.

A ``frame`` is a small, highly bit concerned header + "payload". The payload is any and all application data, similar to the body of a http message.

A frame looks like this::

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-------+-+-------------+-------------------------------+
     |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
     |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
     |N|V|V|V|       |S|             |   (if payload len==126/127)   |
     | |1|2|3|       |K|             |                               |
     +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
     |     Extended payload length continued, if payload len == 127  |
     + - - - - - - - - - - - - - - - +-------------------------------+
     |                               |Masking-key, if MASK set to 1  |
     +-------------------------------+-------------------------------+
     | Masking-key (continued)       |          Payload Data         |
     +-------------------------------- - - - - - - - - - - - - - - - +
     :                     Payload Data continued ...                :
     + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
     |                     Payload Data continued ...                |
     +---------------------------------------------------------------+

`Further reading here. <https://tools.ietf.org/html/rfc6455#section-5.2>`_

All you really need to know is that your application can turn on reserved bits and set custom opcodes in the ranges 3-7 for non-control frames (text or binary data etc.) and 11-15 for control frames (ping/pong and close etc.).

Both control and non-control frames use this structure.

The ``connecting`` state is covered in depth in the next section. It's when the opening handshake takes place.

In the ``open`` state, both client and server may send any type of message to each other at any time, with some minor restrictions.

* Control frames may not be fragmented (must always have FIN bit set to 1) and if they have a payload, the first two bytes must be a websocket status code and the overall payload length must not be greater than 125.
* Non-control frames may not interleave other non-control frames. (If you are sending a non-control message over multiple frames, control frames may interrupt at any point, however frames like 'text' and 'binary' may not.)
* If either side sends a frame who's opcode indicates a ``close`` the connection moves from ``open`` to ``closing`` and all further frames must be discarded. The side that received the ``close`` must respond with a ``close`` frame in kind, placing both sides in a ``closed`` state and ending the websocket connection.

Note: any and all protocol violations, regardless of how minor they are, must result in the (if possible) immediate sending of a ``close`` frame and closure of the connection.

The opening handshake
_____________________

It is not entirely important to know the details of everything that follows, as pretty much all of it is covered by the handshake utils that come with noio_ws. However, if you plan on negotiating extensions or subprotocols you should be familiar with the structuring of the corresponding headers. The handshake utils can only do simplistic validation of extension/subprotocol requests.

All websocket connections start their lives as http GET requests, requesting a websocket resource under the websocket protocol schema ``ws://`` or ``wss://``. These are analogous to ``http://`` and ``https://``. This might seem a little strange, so I'll reiterate again: *the http request is made to a websocket scheme.* An example URI is::

    wss://echo.websocket.org  # this is where we make the http request

The request must have the following::

    * GET resource_location HTTP/1.1
    * host: some_hostname
    * upgrade: websocket  # request an upgrade from http to websockets
    * connection: upgrade # say we are looking for the connection to be upgraded
    * sec-websocket-version: 13  # the current websocket protocol version
    * sec-websocket-key: a_generated_nonce # a b64 encoded randomly generated string of bytes between 0 and 255

Optionally, the client may also send a ``sec-websocket-extensions`` header, and / or a ``sec-websocket-protocol`` header in order to negotiate which extensions and subprotocols to employ (compression extension, chat subprotocol etc.)

Once a client sends this request, the server verifies the request's headers are in order (as they are above) and that the base 64 decoded nonce is of length 16.

If the server is happy with the details of the request, it forms a response to the first part of the handshake.

It looks like this::

    * HTTP/1.1 101 Switching Protocols  # clients request is accepted
    * upgrade: websocket  # upgrading to websocket protocol
    * connection: upgrade  # connection is being upgraded
    * sec-websocket-version: 13  # current websocket protocol version
    * sec-weebsocket-accept: response_nonce  # This value is the string of the client's nonce *as received* concatenated with the websocket GUID, which is then encoded as ``utf-8`` bytes and sha1'd. The resulting sha1's digest is then base64 encoded, and that is the response_nonce. (Bloody madness).

If supplied, the server may also send a ``sec-websocket-extensions`` header, and / or a ``sec-websocket-protocol`` header detailing which (if any) extensions or protocols it agrees to. If there is no agreement made the server closes the connection.

*It is at this point that the server, if it accepts the connection thus far, moves from handling the client as a http client to a websocket client.*

*whew!*

Once the client receives this response, it must then validate that response. *Oh god please, no more :(*

The client ensures the status code is 101, and that the headers are in order. This involves the client independently calculating the response_nonce the server responded with, and checking that against the server's response_nonce. It may also involve the acceptance or rejection of the extensions negotiated by the server, closing the connection if it sees fit (though it would be unusual to reject at this point given that the server would have already rejected and closed if there was a conflict.)

*It is at this point that the client, if it accepts the response from the server, moves from handling the connection as a websocket connection. This is where both sides may be considered in "websocket protocol mode" and may begin sending websocket frames.*

**That's a whole lotta stuff ey?** It is an extremely tedious and miserable exchange. noio_ws treats it as extremely tedious and miserable, and VERY much separates this opening flim-flam from the usage of an open websocket connection. noio_ws provides easy to use handshake utils to deal with the above, however the utils do *not* deal with the negotiation of extensions or subprotocols any more complex than ``'extension_1, extension_2'`` or ``'subprotocol_1, subprotocol_2'``.
