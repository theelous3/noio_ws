.. noio_ws documentation master file, created by sphinx-quickstart, Wed May 17 17:03:44 2017. Thanks sphinx! :D


noio_ws
===================================

Contents:
_________
.. toctree::
   :maxdepth: 2

   overview_of_websockets
   using_noio_ws
   api


What is noio_ws?
________________

noio_ws is a sans-io implementation of the websocket protocol for use in creating both clients and servers. This means that the library does *not* include anything that interacts with networks etc. directly, but instead provides a ``Connection`` object that acts as a middle-man, building frames for stuff you want to send and turning received raw bytes from your network in to ``Message`` objects you can deal with in a simple and sane way.

It's api is modeled after the wonderful `h11 <https://github.com/njsmith/h11>`_ httplib, employing a state-machine-y core that spits out events.


How does noio_ws treat the websocket protocol?
______________________________________________

With calmly measured disdain, mostly. The websocket protocol is heavily intertwined with http, relying on http's protocol switching in an opening handshake before moving on to the websocket Good Stuff. I wanted to compartmentalise the websocket Good Stuff away from the opening handshake Bad Stuff as much as possible, to provide a simple and distinct api for both parts of the life-cycle. This makes it much easier to reason about the application you're building :)

To this end, noio_ws comes with a set of handshake utilities which are direct addons for `h11 <https://github.com/njsmith/h11>`_ . The usage of these is detailed in the rest of the docs.

Installation
____________

noio_ws requires python 3.x+.

Install by doing::

    pip install git+https://github.com/theelous3/noio_ws.git
    # comes with h11

Features
________

noio_ws provides a simple api which affords the absolutely maximum extensibility permitted by the websocket protocol. It is extremely easy to strap on extensions, manipulate reserved bits, and add custom opcodes for both control and non-control frames.

About
_____

noio_ws was created by Mark Jameson

http://theelous3.net

Shoutout to the fine folks of `8banana <https://github.com/8Banana>`_ and co.
