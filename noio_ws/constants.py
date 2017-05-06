from enum import Enum, auto


__all__ = ['MAGIC_STR',
           'CONTROL_FRAMES',
           'TYPE_FRAMES',
           'CONT_FRAME',
           'BASE_ALL_FRAMES',
           'CStates',
           'Roles',
           'RecvrState',
           'Directive',
           'Information']

MAGIC_STR = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

CONTROL_FRAMES = ['close', 'ping', 'pong']
TYPE_FRAMES = ['text', 'binary']
CONT_FRAME = ['continuation']
BASE_ALL_FRAMES = CONTROL_FRAMES + TYPE_FRAMES + CONT_FRAME


class CStates(Enum):
    CONNECTING = auto()
    AWAIT_RESPONSE = auto()
    OPEN = auto()
    CLOSING = auto()
    CLOSED = auto()


class Roles(Enum):
    CLIENT = auto()
    SERVER = auto()


class RecvrState(Enum):
    AWAIT_FRAME_START = auto()
    NEED_LEN = auto()
    NEED_MASK = auto()
    NEED_BODY = auto()
    MSG_RECVD = auto()


class Directive(Enum):
    NEED_DATA = auto()
    SEND_PING = auto()
    SEND_PONG = auto()
    SEND_CLOSE = auto()


class Information(Enum):
    CONNECTION_CLOSED = auto()
