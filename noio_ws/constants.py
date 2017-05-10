from enum import Enum, auto


__all__ = ['MAGIC_STR',
           'CONTROL_FRAMES',
           'TYPE_FRAMES',
           'CONT_FRAME',
           'BASE_ALL_FRAMES',
           'CStates',
           'Roles',
           'RecvrState',
           'Information']

MAGIC_STR = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

CONTROL_FRAMES = ['close', 'ping', 'pong']
TYPE_FRAMES = ['text', 'binary']
CONT_FRAME = ['continuation']
BASE_ALL_FRAMES = CONTROL_FRAMES + TYPE_FRAMES + CONT_FRAME


class CStates(Enum):
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


class Information(Enum):
    NEED_DATA = auto()
    SEND_PING = auto()
    SEND_PONG = auto()
    SEND_CLOSE = auto()
    CONNECTION_CLOSED = auto()


status_codes = {1000: 'Normal Closure',
                1001: 'Going Away',
                1002: 'Protocol Error',
                1003: 'Unsupported Data',
                1005: 'No Status Rcvd',
                1006: 'Abnormal Closure',
                1007: 'Invalid Frame Payload Data',
                1008: 'Policy Violation',
                1009: 'Message Too Big',
                1010: 'Mandatory Ext.',
                1011: 'Internal Server Error',
                1015: 'TLS Handshake'}
