from .constants import *


class Frame:
    def __init__(self, bufferdata):
        self.buffer = bufferdata
        self._type = None
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
        self.opcode = None
        if b1 & 0b1111 == 0b0000:
            self.opcode = 'continuation'
        elif b1 & 0b1111 == 0b0001:
            self.opcode = 'text'
        elif b1 & 0b1111 == 0b0010:
            self.opcode = 'binary'
        elif b1 & 0b1111 == 0b1000:
            self.opcode = 'close'
        elif b1 & 0b1111 == 0b1001:
            self.opcode = 'ping'
        elif b1 & 0b1111 == 0b1010:
            self.opcode = 'pong'
        else:
            raise NnwsProtocolError('Invalid opcode received.')

        # check masked
        if b2 & 0b10000000:
            if ROLE is Roles.CLIENT:
                raise NnwsProtocolError('Masked frame from server.')
            else:
                self.masked = True

        # get length
        self.expected_len = int(bin(b2)[2:].zfill(8)[4:], 2)
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


class Message:
    def __init__(self, message, reserved, control):
        self.message = message
        self.reserved = reserved
        self.control = control
