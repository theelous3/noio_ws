# noio_ws
noio_ws is a sans-io websocket implementation. This means that it does not do any network stuff. It provides a simple api to which you pass bytes, and in return are handed nicely formed websocket messages. noio_ws is built to provide a framework for writing both websocket clients and servers, with the full range of extensibility allowed by the websocket protocol (and more! [It's a protocol, not a cop.](http://i.imgur.com/mSHi8.jpg))


*Requires:* Python 3.x +

## Installation

`pip install git+https://github.com/theelous3/noio_ws.git`

## Docs
Docs are currently slightly out of sync as the lib undergoes some api changes!
[Read 'em!](http://noio-ws.rtfd.io) There you'll find a guide to using noio_ws to write clients and servers as simple or complex as you'd like.

### Notes
This lib is a work in progress, and the api is in flux whilst nice human usable solutions are poked and prodded in to formation.

### Shoutout to ##lp, and the fine peeps of 8banana
