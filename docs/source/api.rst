noio_ws API
===========

``Connection`` object
_____________________

.. py:class:: Connection(role, opcode_non_control_mod=None, opcode_control_mod=None)

    The connection object which acts as a middle man between your application logic and your network io.

    :param str role: Either ``'CLIENT'`` or ``'SERVER'`` used to set the Connection 's role.
    :param dict opcode_non_control_mod: For example ``{'latin-1': 3}``. This adds extensibility for non-control frames. Valid ints are 3-7.
    :param dict opcode_control_mod: For example ``{'compare': 11}``. This adds extensibility for control frames. Vaid ints are 11-15.

    .. py:method:: send(self, data)

        Prepares Data objects, returning bytes ready to be sent over the network.

        :param Data data: Given a ``Data`` object, returns a ``bytes`` object representing a websocket frame suitable to be sent over a network.
        :returns: None

    .. py:method:: recv(self, bytechunk)

        Takes raw bytes fresh from the informationsuperhighway and processes them.

        :param bytes bytechunk: Takes bytes and processes them with the internal receiver class, building a ``Message`` object.
        :returns: None

    .. py:method:: next_event(self)

        Checks to see if there is an event ready internally, handing it back to the caller.

        :returns: ``Message`` object or ``Information.NEED_DATA``

``Data`` object
_______________

.. py:class:: Data(self, data, type, fin=True, status_code=None, rsv_1=None, rsv_2=None, rsv_3=None)

    The object used to represent websocket frames for sending.

    :param str/bytes data: A bytes or string object to be sent as the frame's payload.
    :param str type: The name of the opcode for the frame. For example ``'text'``.
    :param bool fin: Indicates if the frame is the last the series.
    :param int status_code: The int representing the status close for ``close`` frames.
    :param int rsv_1: Passing ``1`` turns on the frame's first reserved bit.
    :param int rsv_2: Passing ``1`` turns on the frame's second reserved bit.
    :param int rsv_3: Passing ``1`` turns on the frame's third reserved bit.

``Message`` object
__________________

.. py:class:: Message(self, message, type, reserved)

    The object used to represent a received websocket frame. Returned to the caller of ``Connection.next_event()`` when there is an event ready.

    .. py:attribute:: .message

        The frame's payload data.

    .. py:attribute:: .type

        The string representation of the opcode. For example ``'text'``, ``'continue'``, ``'close'``.

    .. py:attribute:: .reserved

        A list in the format ``[Int, Int, Int]`` where a ``1`` or ``0`` represents a frame's reserved bit has been turned on or left off. For example ``[1, 0, 0]`` indicates that the first reserved bit in a frame is on.

    .. py:attribute:: .time

        A ``datetime`` object representing when the frame was received.
