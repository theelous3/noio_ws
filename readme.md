# noio_ws
noio_ws is a sans-io websocket implementation. This means that it does not do any network stuff. It provides a simple api to which you pass bytes, and in return are handed nicely formed websocket messages. noio_ws is built to provide a framework for writing both websocket clients and servers, with the full range of extensibility allowed by the websocket protocol (and more! [It's a protocol, not a cop.](http://i.imgur.com/mSHi8.jpg))


*Requires:* Python 3.x +

## Installation

`pip install git+https://github.com/theelous3/noio_ws.git`

## Docs
[Read 'em!](http://noio-ws.rtfd.io) There you'll find a guide to using noio_ws to write clients and servers as simple or complex as you'd like.

### Notes
This lib is a work in progress, however the pure websocket stuff is quite well polished and ready to go. The opening handshake, by its very nature, is awful to work with. The current task is working out a nice user-usable api for dealing with extension and protocol negotiation.

### Shoutout to ##lp, and the fine peeps of 8banana
