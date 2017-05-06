from .constants import *
from .utils import mask_unmask

__all__ = ['Frame', 'Message', 'Data']


class Message:
    def __init__(self, message, type, reserved):
        self.message = message
        self.type = type
        self.reserved = reserved


class Frame:
    def __init__(self, bufferdata, opcodes):
        self.buffer = bufferdata
        self.opcodes = opcodes
        self.fin = False
        self.resrvd = [0, 0, 0]
        self.opcode = None
        self.masked = False
        self.mask = None
        self.expected_len = 0
        self.l_bound = 0
        self.pl_strt = 2

        self.payload = bytearray()

        self.frame_size = 0

    def proc(self, ROLE):
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
                (ophrase for ophrase, opcode in self.opcodes.items()
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
        self.buffer.extend(frame.buffer)
        for index, rsrv in enumerate(self.resrvd):
            if not rsrv and frame.resrvd[index]:
                self.resrvd[index] = frame.resrvd[index]
        self.frame_size += frame.frame_size
        self.payload.extend(frame.payload)
        self.fin = frame.fin


class Data:

    def __init__(self, data, type, fin):
        self.data = data
        self.type = type

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

    def __call__(self, role, opcodes):
        self.data = bytesify(self.data)

        bytes_to_go = bytearray()
        close = False
        if self.type == 'close':
            close = True

        byte_0 = 0
        if self.fin:
            byte_0 = byte_0 | 1 << 7

        opcode = opcodes[self.type]
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
