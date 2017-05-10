from .errors import NnwsProtocolError
from .structs import *
from .constants import *
from .utils import mask_unmask

__all__ = ['Connection']


class Connection:
    def __init__(self,
                 role,
                 opcode_type_mod=None,
                 opcode_control_mod=None,
                 rsrv_mod=None):
        if role == 'CLIENT':
            self.role = Roles.CLIENT
        elif role == 'SERVER':
            self.role = Roles.SERVER
        else:
            raise TypeError(role, 'is not a valid role.')

        self.state = CStates.OPEN
        self.close_init_client = False
        self.close_init_server = False

        self.opcodes = {'continuation': 0,
                        'text': 1,
                        'binary': 2,
                        'close': 8,
                        'ping': 9,
                        'pong': 10}
        if opcode_type_mod:
            if all(opcode != given_opcode and given_opcode < 15
                   for _, opcode in self.opcodes.items()
                   for _, given_opcode in opcode_type_mod):
                self.opcodes.update(opcode_type_mod)
                global TYPE_FRAMES
                TYPE_FRAMES.extend([opphrase for opphrase, _ in
                                    opcode_type_mod.items()])
            else:
                raise ValueError('Cannot overwrite default opcode.')
        if opcode_control_mod:
            if all(opcode != given_opcode and given_opcode < 15
                   for _, opcode in self.opcodes.items()
                   for _, given_opcode in opcode_control_mod):
                self.opcodes.update(opcode_control_mod)
                global CONTROL_FRAMES
                CONTROL_FRAMES.extend([opphrase for opphrase, _
                                       in opcode_control_mod.items()])
            else:
                raise ValueError('Cannot overwrite default opcode.')

        self.recvr = Recvr(self.role, self.opcodes)
        self.event = None

    def recv(self, bytechunk):
        print('gonna recv')
        event = self.recvr(bytechunk)
        if self.state is CStates.OPEN:
            if isinstance(event, Message):
                self.event = event
                if self.event.type == 'close':
                    if self.close_init_client:
                        self.state = CStates.CLOSED
                    else:
                        self.close_init_server = True
                        self.state = CStates.CLOSING

        elif self.state is CStates.CLOSING:
            if self.close_init_client:
                if isinstance(event, Message):
                    self.event = event
            elif self.close_init_server:
                self.event = Information.SEND_CLOSE

        else:  # self.state is CStates.CLOSED:
            raise NnwsProtocolError('Trying to recv data on closed connection')

    def send(self, data):
        if self.state is CStates.OPEN:
            if isinstance(data, Data):
                byteball, close = data(self.role, self.opcodes)
                if close:
                    if self.close_init_server:
                        self.state = CStates.CLOSED
                    else:
                        self.close_init_client = True
                        self.state = CStates.CLOSING
        elif self.state is CStates.CLOSING:
            byteball, close = data(self.role, self.opcodes)
            if not close:
                raise NnwsProtocolError('Cannot send non-close frame in '
                                        'closing state')
        else:  # self.state is CStates.CLOSED:
            raise NnwsProtocolError('Trying to send data on closed connection')

        return byteball

    def next_event(self):
        if self.state is CStates.OPEN:
            if self.event is not None:
                returnable = self.event
                self.event = None
            else:
                returnable = Information.NEED_DATA
        elif self.state is CStates.CLOSING:
            if self.event is not None:
                returnable = self.event
                self.event = None
            else:
                if self.close_init_client:
                    returnable = Information.NEED_DATA
                if self.close_init_server:
                    returnable = Information.SEND_CLOSE
        else:  # self.state is CStates.CLOSED:
            raise NnwsProtocolError('Trying to recv data on closed connection')
        return returnable


class Recvr:

    def __init__(self, role, opcodes):
        self.data_f = None
        self.f = None

        self.buffer = bytearray()

        self.state = RecvrState.AWAIT_FRAME_START
        self.role = role
        self.opcodes = opcodes

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
            return Information.NEED_DATA
        self.f = Frame(self.buffer, self.opcodes)
        self.f.proc(self.role)
        if self.f.l_bound:
            self.state = RecvrState.NEED_LEN
        elif self.f.masked:
            self.state = RecvrState.NEED_MASK
        else:
            self.state = RecvrState.NEED_BODY

    def need_len(self, bytechunk):
        print('We find da len')
        if bytechunk is not None:
            self.f.buffer.extend(bytechunk)
        if len(self.f.buffer) < 2 + self.f.l_bound:
            return Information.NEED_DATA
        self.f.expected_len = int.from_bytes(
            self.f.buffer[2:2+self.f.l_bound], 'big')
        if self.f.masked:
            self.state = RecvrState.NEED_MASK
        else:
            self.f.pl_strt = 2 + self.f.l_bound
            self.state = RecvrState.NEED_BODY

    def need_mask(self, bytechunk):
        print('We gettin da mesk')
        if bytechunk is not None:
            self.f.buffer.extend(bytechunk)
        if self.f.l_bound:
            if len(self.f.buffer) < 6 + self.f.l_bound:
                return Information.NEED_DATA
            self.mask = self.f.buffer[2+self.f.l_bound:6+self.f.l_bound]
            self.f.pl_strt = 7 + self.f.l_bound
        else:
            if len(self.f.buffer) < 7:
                return Information.NEED_DATA
            self.f.mask = self.f.buffer[2:6]
            self.f.pl_strt = 6
        self.state = RecvrState.NEED_BODY

    def need_body(self, bytechunk):
        print('We need gettin da bodi')
        if bytechunk is not None:
            self.f.buffer.extend(bytechunk)
        if len(self.f.buffer[self.f.pl_strt:]) < self.f.expected_len:
            return Information.NEED_DATA
        self.f.raw_len = self.f.pl_strt + self.f.expected_len
        if not self.f.masked:
            self.f.payload.extend(self.f.buffer[self.f.pl_strt:self.f.raw_len])
        else:
            self.f.payload.extend(
                mask_unmask(
                    self.f.buffer[self.f.pl_strt:self.f.raw_len], self.f.mask))
        self.state = RecvrState.MSG_RECVD

    def msg_recvd(self):
        print('We has da mesug')
        self.buffer = self.f.buffer[self.f.raw_len:]
        if self.f.opcode in TYPE_FRAMES:
            if not self.data_f:
                if self.f.fin:
                    if self.f.opcode == 'text':
                        self.f.payload = str(self.f.payload, 'utf-8')
                    returnable = Message(
                        self.f.payload, self.f.opcode, self.f.resrvd)
                else:
                    self.data_f = self.f
                    returnable = Information.NEED_DATA
            else:
                self.f = None
                raise NnwsProtocolError('Attempted to interleave '
                                        'non-control frames.')
        elif self.f.opcode == 'continuation':
            if self.data_f:
                self.data_f.incorporate(self.f)
                if self.data_f.fin:
                    returnable = Message(self.data_f.payload,
                                         self.data_f.opcode,
                                         self.data_f.resrvd)
                    self.data_f = None

        elif self.f.opcode in CONTROL_FRAMES:
            if self.f.fin:
                returnable = Message(
                    bytes(self.f.payload), self.f.opcode, self.f.resrvd)
            else:
                self.f = None
                raise NnwsProtocolError('Fragmented control frame.')

        self.state = RecvrState.AWAIT_FRAME_START
        self.f = None

        return returnable
