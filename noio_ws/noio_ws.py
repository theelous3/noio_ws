from urllib.parse import urlparse, urlunparse
from random import randint, getrandbits
from base64 import b64encode, b64decode

import h11

from .errors import NnwsProtocolError
from .structs import Frame, Message
from .constants import *


class Connection:
    def __init__(self, role, subprotocols=None, extensions=None, host=None):
        self.host = host
        if role == 'CLIENT':
            self.role = Roles.CLIENT
        elif role == 'SERVER':
            self.role = Roles.SERVER
            try:
                assert self.host
            except AssertionError:
                raise NnwsProtocolError('Must supply a host with Role.SERVER')
        else:
            raise AttributeError(role, 'is not a valid role.')

        self.state = CStates.OPEN
        self.close_init_client = False
        self.close_init_server = False

        self.subprotocols = None
        self.extensions = None

        self.recvr = Recvr(self.role)
        self.event = None

    def recv(self, stuff):
        if self.state is CStates.OPEN:
            self.event = self.recvr(stuff)
            if isinstance(self.event, Message):
                if self.event.control == 'close':
                    if self.close_init:
                        self.state = CStates.CLOSED
                    else:
                        self.close_init_server = True
                        self.state = CStates.CLOSING

        if self.state is CStates.CLOSING:
            self.event = Directive.SEND_CLOSE

        if self.state is CStates.CLOSED:
            raise NnwsProtocolError('Trying to recv data on closed connection')

    def send(self, data):
        if self.state is CStates.OPEN:
            if isinstance(data, Data):
                byteball, close = data(self.role)
                if close:
                    if self.close_init:
                        self.state = CStates.CLOSED
                    else:
                        self.close_init_client = True
                        self.state = CStates.CLOSING
        if self.state is CStates.CLOSING:
            byteball, close = data()
            if not close:
                raise NnwsProtocolError('Cannot send non-close frame in '
                                        'closing state')
        if self.state is CStates.CLOSED:
            raise NnwsProtocolError('Trying to send data on closed connection')

        return byteball

    def next_event(self):
        if self.state is CStates.OPEN:
            if self.event is not None:
                returnable = self.event
                self.event = None
            else:
                returnable = Directive.NEED_DATA
            return returnable
        if self.state is CStates.CLOSING:
            if self.event is not None:
                returnable = self.event
                self.event = None
            else:
                if self.close_init_client:
                    returnable = Directive.NEED_DATA
                if self.close_init_server:
                    returnable = Directive.SEND_CLOSE
            return returnable
        if self.state is CStates.CLOSED:
            return None


class Recvr:

    def __init__(self, role):
        self.data_f = None
        self.f = None

        self.buffer = bytearray()

        self.state = RecvrState.AWAIT_FRAME_START
        self.role = role

    def __call__(self, bytechunk):
        if self.state is RecvrState.AWAIT_FRAME_START:
            if bytechunk:
                self.buffer.extend(bytechunk)
                bytechunk = None
            result = self.await_start()
            if result is not None:
                return result
            self.buffer = bytearray()

        if self.state is RecvrState.NEED_LEN:
            result = self.need_len(bytechunk)
            if result is not None:
                return result

        if self.state is RecvrState.NEED_MASK:
            result = self.need_mask(bytechunk)
            if result is not None:
                return result

        if self.state is RecvrState.NEED_BODY:
            result = self.need_body(bytechunk)
            if result is not None:
                return result

        if self.state is RecvrState.MSG_RECVD:
            return self.msg_recvd()

    def await_start(self):
        if len(self.buffer) < 2:
            return Directive.NEED_DATA
        self.f = Frame(self.buffer)
        self.f.proc(self.role)
        if self.f.l_bound:
            self.state = RecvrState.NEED_LEN
        elif self.f.masked:
            self.state = RecvrState.NEED_MASK
        else:
            self.state = RecvrState.NEED_BODY

    def need_len(self, bytechunk):
        if bytechunk is not None:
            self.f.buffer.extend(bytechunk)
        if len(self.f.buffer) < 2 + self.f.l_bound:
            return Directive.NEED_DATA
        self.f.expected_len = int.from_bytes(
            self.f.buffer[2:2+self.f.l_bound], 'big')
        if self.f.masked:
            self.state = RecvrState.NEED_MASK
        else:
            self.f.pl_strt = 2 + self.f.l_bound
            self.state = RecvrState.NEED_BODY

    def need_mask(self, bytechunk):
        if bytechunk is not None:
            self.f.buffer.extend(bytechunk)
        if self.f.l_bound:
            if len(self.f.buffer) < 6 + self.f.l_bound:
                return Directive.NEED_DATA
            self.mask = self.f.buffer[2+self.f.l_bound:6+self.f.l_bound]
            self.f.pl_strt = 7 + self.f.l_bound
        else:
            if len(self.f.buffer) < 7:
                return Directive.NEED_DATA
            self.f.mask = self.f.buffer[2:6]
            self.f.pl_strt = 6
        self.state = RecvrState.NEED_BODY

    def need_body(self, bytechunk):
        if bytechunk is not None:
            self.f.buffer.extend(bytechunk)
        if len(self.f.buffer[self.f.pl_strt:]) < self.f.expected_len:
            return Directive.NEED_DATA
        self.f.raw_len = self.f.pl_strt + self.f.expected_len
        if not self.f.masked:
            self.f.payload.extend(self.f.buffer[self.f.pl_strt:self.f.raw_len])
        else:
            self.f.payload.extend(
                mask_unmask(
                    self.f.buffer[self.f.pl_strt:self.f.raw_len], self.f.mask))
        self.state = RecvrState.MSG_RECVD

    def msg_recvd(self):
        self.buffer = self.f.buffer[self.f.raw_len:]
        if self.f.opcode in TYPE_FRAMES:
            if not self.data_f:
                if self.f.fin:
                    returnable = Message(
                        bytes(self.f.payload), self.f.resrvd, None)
                else:
                    self.data_f = self.f
                    returnable = Directive.NEED_DATA
            else:
                self.f = None
                raise NnwsProtocolError('Attempted to interleave '
                                        'non-control frames.')
        if self.f.opcode == 'continuation':
            if self.data_f:
                self.data_f.incorporate(self.f)
                if self.data_f.fin:
                    returnable = Message(
                        bytes(self.data_f.payload), self.data_f.resrvd, None)
                    self.data_f = None

        if self.f.opcode in CONTROL_FRAMES:
            if self.f.fin:
                returnable = Message(
                    bytes(self.f.payload), self.f.resrvd, self.f.opcode)
            else:
                self.f = None
                raise NnwsProtocolError('Fragmented control frame.')

        self.state = RecvrState.AWAIT_FRAME_START
        self.f = None

        return returnable


class Data:

    def __init__(self, data, type, fin):
        self.data = data
        if type in BASE_ALL_FRAMES:
            self.type = type
        else:
            raise ValueError('Unrecognised value for type:', type)

        if fin is False:
            if self.type not in CONTROL_FRAMES:
                self.fin = fin
            else:
                raise NnwsProtocolError('Trying to fragment'
                                        'control frame:', self.type)
        elif fin is True:
            self.fin = fin
        else:
            raise ValueError('Invalid value for fin:', fin)

    def __call__(self, role):
        self.data = bytesify(self.data)

        bytes_to_go = bytearray()
        close = False

        byte_0 = 0
        if self.fin:
            byte_0 = byte_0 | 1 << 7

        if self.type == 'continuation':
            opcode = 0
        elif self.type == 'text':
            opcode = 1
        elif self.type == 'binary':
            opcode = 2
        elif self.type == 'close':
            opcode = 8
            close = True
        elif self.type == 'ping':
            opcode = 9
        elif self.type == 'pong':
            opcode = 10

        byte_0 = byte_0 | opcode
        bytes_to_go.append(byte_0)

        byte_1 = 0
        mask = None

        if role is Roles.CLIENT:
            byte_1 = byte_1 | 1 << 7
            mask = getrandbits(32).to_bytes(4, 'big')
            self.data = mask_unmask(self.data, mask)

        data_len = len(self.data)
        if data_len <= 125:
            len_flag = data_len
        elif data_len <= 65535:
            len_flag = 126
        elif data_len <= 9223372036854775807:
            len_flag = 127
        else:
            raise NnwsProtocolError('Data > 8.388 million TB, you lunatic.')
        byte_1 = byte_1 | len_flag
        bytes_to_go.append(byte_1)

        if len_flag in [126, 127] and self.type in CONTROL_FRAMES:
            raise NnwsProtocolError('Payload too big for'
                                    'control frame.'
                                    '{}/125:'.format(data_len))

        if len_flag == 126:
            bytes_to_go.append(data_len.to_bytes(2, 'big'))
        elif len_flag == 127:
            bytes_to_go.append(data_len.to_bytes(8, 'big'))

        if mask is not None:
            bytes_to_go.extend(mask)

        bytes_to_go.extend(self.data)
        return bytes(bytes_to_go), close


def mask_unmask(data, mask):
    for i, x in enumerate(data):
        data[i] = x ^ mask[i % 4]
    return data


def bytesify(data):
    if isinstance(data, str):
        data = bytearray(data, 'utf-8')
    elif isinstance(data, bytes):
        data = bytearray(data)
    elif isinstance(data, bytearray):
        pass
    else:
        raise NnwsProtocolError('Trying to send non-binary or non-utf8 data.')
    return data
