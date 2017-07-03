from random import getrandbits
from datetime import datetime

from .constants import *
from .handshake_utils import mask_unmask


__all__ = ['FrameParser',
           'BaseFrame',
           'Message',
           'ReceivedFrame',
           'ControlMessage',
           'TypeFrameBuffer',
           'SendFrame']


class BaseFrame:
    def __init__(self, payload, f_type, reserved):
        '''The base type for all received frames.'''
        self.payload = payload
        self.f_type = f_type
        self.reserved = reserved
        self.time = datetime.now()

    @property
    def data(self):
        '''More memory efficient access to the payload attribute.
        Works a bit like a one time iterator.'''
        content = self.payload
        self.payload = bytearray()
        return content

    def __repr__(self):
        repr_str = ('{}:(payload="{}", f_type="{}",reserved={}, ' +
                    'time={})')
        return repr_str.format(
            hex(id(self)),
            str(self.payload[:9]) + ('[...]' if len(self.payload) > 9 else ''),
            self.f_type,
            self.reserved,
            self.time)


class Message(BaseFrame):
    '''The type of frame used for full message interactions.'''
    pass


class ReceivedFrame(BaseFrame):
    '''The type of frame used for interactions where partial frames are
    events.'''
    def __init__(self, fin=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fin = fin

    def combine(self, frame_obj):
        self.fin = frame_obj.fin
        self.payload.extend(frame_obj.payload)
        self.reserved = frame_obj.reserved
        self.time = frame_obj.time


class ControlMessage(BaseFrame):
    '''The frame type used for control frames.'''
    pass


class TypeFrameBuffer:
    '''A special buffer used to collect ReceivedFrames, such that the
    frames headers are kept up to date along with fragmented frames.
    Basically a wrapper.'''
    def __init__(self):
        self.f = None

    def add(self, f):
        if self.f is None:
            self.f = f
        else:
            if self.f.fin:
                self.f = f
            else:
                self.f.combine(f)

    def combine(self, message_obj):
        self.f.combine(message_obj)

    @property
    def data(self):
        return self.f.data

    @property
    def payload(self):
        return self.f.payload

    @property
    def f_type(self):
        return self.f.f_type

    @property
    def reserved(self):
        return self.f.reserved

    @property
    def time(self):
        return self.f.time

    @property
    def fin(self):
        return self.f.fin


class FrameParser:
    '''The parser class that deals with parsing an incoming frame's
    headers.'''
    def __init__(self, bufferdata, opcodes):
        self.buffer = bufferdata
        self.opcodes = opcodes
        self.fin = False
        self.resrvd = [0, 0, 0]
        self.opcode = None
        self.masked = False
        self.mask = None

        self.expected_len = 0
        self.remaining_len = 0

        self.l_bound = 0
        self.pl_strt = 2

        self.payload = bytearray()

        self.frame_size = 0

    def proc(self, ROLE):
        '''When sufficient bytes have been received, the parsing of a frame
        can begin. This proc method is...procced, and so begins the parsing.'''
        b1, b2 = self.buffer[:2]
        # check fin
        if b1 & 0b10000000:
            self.fin = True
        # check rsvd
        if b1 & 0b01000000:
            self.resrvd[0] = 1
        if b1 & 0b00100000:
            self.resrvd[1] = 1
        if b1 & 0b00010000:
            self.resrvd[2] = 1

        # check opcode
        try:
            self.opcode = next(
                (ophrase for opcode, ophrase in self.opcodes.items()
                 if b1 & 0b1111 == opcode))
        except StopIteration:
            raise NnwsProtocolError('Invalid opcode received.')

        # check masked
        if b2 & 0b10000000:
            if ROLE is Roles.CLIENT:
                raise NnwsProtocolError('Masked frame from server.')
            else:
                self.masked = True

        # get length
        self.expected_len = int(bin(b2)[2:].zfill(8)[1:], 2)
        if self.expected_len <= 125:
            pass
        elif self.expected_len == 126:
            self.l_bound = 4
        elif self.expected_len == 127:
            self.l_bound = 10
        else:
            raise NnwsProtocolError('Bad len indicator:',
                                    self.expected_len)

    def incorporate(self, frame):
        '''Incorporates one frame in to another, used to combine multiple
        frames in to full Message objects.'''
        self.buffer.extend(frame.buffer)
        for index, rsrv in enumerate(self.resrvd):
            if not rsrv and frame.resrvd[index]:
                self.resrvd[index] = frame.resrvd[index]
        self.frame_size += frame.frame_size
        self.payload.extend(frame.payload)
        self.fin = frame.fin


class SendFrame:
    '''The class used to construct frames for sending over network.'''
    def __init__(self, data, f_type, fin=True, status_code=None,
                 rsv_1=None, rsv_2=None, rsv_3=None):
        self.data = data
        self.f_type = f_type

        if fin is False:
            if self.f_type not in CONTROL_FRAMES:
                self.fin = fin
            else:
                raise NnwsProtocolError('Trying to fragment'
                                        'control frame:', self.f_type)
        elif fin is True:
            self.fin = fin
        else:
            raise ValueError('Invalid value for fin:', fin)

        self.status_code = status_code

        if rsv_1 is not None:
            if (rsv_1 == 0 or rsv_1 == 1):
                self.rsv_1 = rsv_1
            else:
                raise ValueError('Invalid value for reserve:', rsv_1)
        else:
            self.rsv_1 = rsv_1
        if rsv_2 is not None:
            if (rsv_2 == 0 or rsv_2 == 1):
                self.rsv_2 = rsv_2
            else:
                raise ValueError('Invalid value for reserve:', rsv_2)
        else:
            self.rsv_2 = rsv_2
        if rsv_3 is not None:
            if (rsv_3 == 0 or rsv_3 == 1):
                self.rsv_3 = rsv_3
            else:
                raise ValueError('Invalid value for reserve:', rsv_3)
        else:
            self.rsv_3 = rsv_3

    def __call__(self, role, opcodes):
        '''When the instance is called, a bunch'a operations take place that
        turn the frame in to a network suitable bytes object.'''
        self.data = bytesify(self.data)

        bytes_to_go = bytearray()
        close = False
        if self.f_type == 'close':
            close = True
            if self.data:
                assert (1000 <= self.status_code <= 1015 or
                        4000 <= self.status_code <= 4999)
                self.data = self.status_code.to_bytes(2, 'big') + self.data

        byte_0 = 0
        if self.fin:
            byte_0 = byte_0 | 1 << 7
        if self.rsv_1:
            byte_0 = byte_0 | 1 << 6
        if self.rsv_2:
            byte_0 = byte_0 | 1 << 5
        if self.rsv_3:
            byte_0 = byte_0 | 1 << 4

        opcode = next((k for k, v in opcodes.items() if v == self.f_type))
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

        if len_flag in [126, 127] and self.f_type in CONTROL_FRAMES:
            raise NnwsProtocolError('Payload too big for'
                                    'control frame.'
                                    '{}/125:'.format(data_len))

        if len_flag == 126:
            bytes_to_go.extend(data_len.to_bytes(2, 'big'))
        elif len_flag == 127:
            bytes_to_go.extend(data_len.to_bytes(8, 'big'))

        if mask is not None:
            bytes_to_go.extend(mask)

        bytes_to_go.extend(self.data)
        return bytes(bytes_to_go), close


def bytesify(data):
    '''Turns things in to bytes.'''
    if isinstance(data, str):
        data = bytearray(data, 'utf-8')
    elif isinstance(data, bytes):
        data = bytearray(data)
    elif isinstance(data, bytearray):
        pass
    else:
        raise NnwsProtocolError('Trying to send non-binary or non-utf8 data.')
    return data
