from urllib.parse import urlparse, urlunparse
from random import randint, getrandbits
from base64 import b64encode
from enum import Enum, auto

import asks
import curio
import wsproto

import h11

from errors import NnwsProtocolError


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
    INITIATE_HANDSHAKE = auto()
    AWAIT_RESPONSE = auto()
    NEED_DATA = auto()


class Message:
    def __init__(self, message, reserved, control):
        self.message = message
        self.reserved = reserved
        self.control = control

ROLE = Roles.CLIENT

HCONN = None

MAGIC_STR = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

CONTROL_FRAMES = ['close', 'ping', 'pong']
NON_CONTROL_FRAMES = ['text', 'binary']
CONT_FRAME = ['continuation']
BASE_ALL_FRAMES = CONTROL_FRAMES + NON_CONTROL_FRAMES + CONT_FRAME


class Connection:
    def __init__(self, role):
        if role == 'CLIENT':
            self.role = Roles.CLIENT
        elif role == 'SERVER':
            self.role = Roles.SERVER
        else:
            raise AttributeError(role, 'is not a valid role.')
        global ROLE
        ROLE = self.role

        self.state = CStates.CONNECTING
        self.close_init = False

        self.nonce = None
        self.req_subprotocols = None
        self.req_extensions = None
        self.subprotocols = None
        self.extensions = None

        self.recvr = Recvr()

    def recv(self, bytechunk):
        if self.state is CStates.AWAIT_RESPONSE:
            self.subprotocols, self.extensions = verify_response(
                bytechunk, self.nonce)
            self.state = CStates.OPEN

    def send(self, data):
        if self.state is CStates.CONNECTING:
            if isinstance(data, Handshake):
                byteball, nonce, protos, extens = data()
                self.nonce = nonce
                self.req_subprotocols = protos
                self.req_extensions = extens
                self.state = CStates.AWAIT_RESPONSE
            else:
                NnwsProtocolError('An opening handshake is required'
                                  ' before sending other data.')
        if self.state is CStates.OPEN:
            if isinstance(data, Data):
                byteball, close = data()
                if close:
                    if self.close_init:
                        self.state = CStates.CLOSED
                    else:
                        self.state = CStates.CLOSING

        return byteball

    def next_event(self):
        if self.state is CStates.CONNECTING:
            return Directive.INITIATE_HANDSHAKE
        elif self.state is CStates.AWAIT_RESPONSE:
            return Directive.AWAIT_RESPONSE


class Recvr:

    def __init__(self):
        self.d_buffer = bytearray()
        self.c_buffer = bytearray()
        self.agnostic_buffer = bytearray()

        self.in_d_frame = False

        self.data = bytearray()
        self.c_data = bytearray()

        self.data_fin = False
        self.control_fin = False
        self.agnostic_fin = False

        self.state = RecvrState.AWAIT_FRAME_START

        self.data_resrvd = [0, 0, 0]
        self.control_resrvd = [0, 0, 0]
        self.agnostic_resrvd = [0, 0, 0]

        self.control = None
        self.expected_len = 0
        self.len_so_far = 0
        self.data_starts = 0

        self.l_bound = False

        self.masked = False
        self.mask = None

    def __call__(self, bytechunk):
        d = self.__dict__
        global ROLE
        ROLE = Roles.SERVER
        if self.state is RecvrState.AWAIT_FRAME_START:
            self.agnostic_buffer.extend(bytechunk)
            bytechunk = None
            if len(self.agnostic_buffer) < 2:
                return Directive.NEED_DATA
            b1, b2 = self.agnostic_buffer[:2]
            # check fin
            if b1 & 0b10000000:
                self.agnostic_fin = True
            # check rsvd
            if b1 & 0b01000000:
                self.agnostic_resrvd[0] = 1
            if b1 & 0b00100000:
                self.agnostic_resrvd[1] = 1
            if b1 & 0b00010000:
                self.agnostic_resrvd[2] = 1
            # check opcode
            opcode = None
            if b1 & 0b1111 == 0b0000:
                opcode = 'continuation'
            elif b1 & 0b1111 == 0b0001:
                opcode = 'text'
            elif b1 & 0b1111 == 0b0010:
                opcode = 'binary'
            elif b1 & 0b1111 == 0b1000:
                opcode = 'close'
            elif b1 & 0b1111 == 0b1001:
                opcode = 'ping'
            elif b1 & 0b1111 == 0b1010:
                opcode = 'pong'
            else:
                raise NnwsProtocolError('Invalid opcode received.')
            if opcode in CONTROL_FRAMES:
                self.control = opcode
                self.c_buffer.extend(self.agnostic_buffer)
                self.control_fin = self.agnostic_fin
                if self.control_fin is not True:
                    raise NnwsProtocolError('Fragmented control frame.')
                self.control_resrvd = self.agnostic_resrvd
                self.a_buffer = 'c_buffer'
                self.a_data = 'c_data'
                self.a_fin = 'control_fin'
                self.a_resrvd = 'control_resrvd'
            else:
                if not self.in_d_frame:
                    if opcode in NON_CONTROL_FRAMES:
                        self.in_d_frame = True
                else:
                    if opcode in NON_CONTROL_FRAMES:
                        raise NnwsProtocolError('Attempting to interleave'
                                                'data frames.')
                self.d_buffer.extend(self.agnostic_buffer)
                self.data_fin = self.agnostic_fin
                if self.data_fin is True:
                    self.in_d_frame = False
                for index, resrvd in enumerate(self.data_resrvd):
                    if resrvd is 0:
                        self.data_resrvd[index] = self.agnostic_resrvd[index]
                self.data_resrvd = self.agnostic_resrvd
                self.a_buffer = 'd_buffer'
                self.a_data = 'data'
                self.a_fin = 'data_fin'
                self.a_resrvd = 'data_resrvd'

            self.agnostic_resrvd = [0, 0, 0]
            self.agnostic_fin = False
            self.agnostic_buffer = bytearray()

            # check masked
            if b2 & 0b10000000:
                if ROLE is Roles.CLIENT:
                    raise NnwsProtocolError('Masked frame from server.')
                else:
                    self.masked = True

            # get length
            self.expected_len = int(bin(b2)[4:], 2)

            if self.expected_len <= 125:
                self.expected_len = self.expected_len
                if self.masked:
                    self.state = RecvrState.NEED_MASK
                else:
                    self.data_starts = 2
                    self.state = RecvrState.NEED_BODY

            elif self.expected_len == 126:
                self.l_bound = 4
            elif self.expected_len == 127:
                self.l_bound = 10
            else:
                raise NnwsProtocolError('Bad len indicator:',
                                        self.expected_len)
            if self.l_bound:
                self.state = RecvrState.NEED_LEN

        if self.state is RecvrState.NEED_LEN:
            if bytechunk is not None:
                d[self.a_buffer].extend(bytechunk)
            if len(d[self.a_buffer]) < 2 + self.l_bound:
                return Directive.NEED_DATA
            self.expected_len = int.from_bytes(
                d[self.a_buffer][2:2+self.l_bound], 'big')

            if self.masked:
                self.state = RecvrState.NEED_MASK
            else:
                self.data_starts = 2 + self.l_bound
                self.state = RecvrState.NEED_BODY

        if self.state is RecvrState.NEED_MASK:
            if bytechunk is not None:
                d[self.a_buffer].extend(bytechunk)
            if self.l_bound:
                if len(d[self.a_buffer]) < 6 + self.l_bound:
                    return Directive.NEED_DATA
                self.mask = d[self.a_buffer][2+self.l_bound:6+self.l_bound]
                self.data_starts = 7 + self.l_bound
            else:
                if len(d[self.a_buffer]) < 7:
                    return Directive.NEED_DATA
                self.mask = d[self.a_buffer][2:6]
                self.data_starts = 6
            self.state = RecvrState.NEED_BODY

        if self.state is RecvrState.NEED_BODY:
            if bytechunk is not None:
                d[self.a_buffer].extend(bytechunk)
            if len(d[self.a_buffer][self.data_starts:]) < self.expected_len:
                return Directive.NEED_DATA
            if not self.masked:
                d[self.a_data].extend(d[self.a_buffer][self.data_starts:])
            else:
                d[self.a_data].extend(
                    mask_unmask(
                        d[self.a_buffer][self.data_starts:], self.mask))
            self.state = RecvrState.MSG_RECVD

        if self.state is RecvrState.MSG_RECVD:
            d[self.a_buffer] = d[self.a_buffer][self.data_starts+len(
                d[self.a_data]):]
            if d[self.a_fin]:
                returnable = Message(
                    bytes(d[self.a_data]), d[self.a_resrvd], self.control)
                d[self.a_data] = bytearray()
                d[self.a_data] = d[self.a_data]
                d[self.a_fin] = False
                d[self.a_resrvd] = [0, 0, 0]
            else:
                returnable = Directive.NEED_DATA

            self.state = RecvrState.AWAIT_FRAME_START
            self.expected_len = 0
            self.len_so_far = 0
            self.data_starts = 0
            self.l_bound = False
            self.masked = False
            self.mask = None

            return returnable


class Handshake:
    def __init__(self, uri, *, protocols=None, extensions=None, **kwargs):
        self.uri = uri
        self.protocols = protocols
        self.extensions = extensions
        self.kwargs = kwargs

    def __call__(self):
        global HCONN
        if ROLE is Roles.CLIENT:
            HCONN = h11.Connection(our_role=h11.CLIENT)
        else:
            HCONN = h11.Connection(our_role=h11.SERVER)
        scheme, netloc, path, _, _, _ = urlparse(self.uri)
        try:
            netloc, port = netloc.split(':', 1)
        except ValueError:
            if scheme.lower() == 'wss':
                port = '443'
            elif scheme.lower() == 'ws':
                port = '80'
            else:
                raise ValueError('Supplied bad location schema')
        request_uri = urlunparse((scheme, netloc, path, '', '', ''))
        nonce = initial_nonce_constructor()
        headers = {'host': ':'.join((netloc, port)),
                   'upgrade': 'websocket',
                   'connection': 'upgrade',
                   'sec-websocket-key': nonce,
                   'sec-websocket-version': '13'}
        if self.protocols:
            headers.update({'sec-websocket-protocol': self.protocols})
        if self.extensions:
            headers.update({'sec-websocket-extensions': self.extensions})
        if self.kwargs:
            headers.update(self.kwargs)
        byteball = HCONN.send(h11.Request(
            method='GET', target=request_uri, headers=headers.items())) + b'\n'
        HCONN.send(h11.EndOfMessage())
        return byteball, nonce, protocols, extensions


class Data:

    CONTROL_FRAMES = ['close', 'ping', 'pong']
    BASE_ALL_FRAMES = CONTROL_FRAMES + ['continuation', 'text', 'binary']

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

    def __call__(self):
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

        global ROLE
        if ROLE is Roles.CLIENT:
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
        return bytes_to_go, close


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


def initial_nonce_constructor():
    return b64encode(bytearray([randint(0, 255) for _ in range(1, 17)]))


def secondary_nonce_constructor(nonce):
    concatd_nonce = str(nonce, 'utf-8') + MAGIC_STR
    concatd_nonce = hashlib.sha1(concatd_nonce.encode('utf-8')).digest()
    concatd_nonce = b64encode(concatd_nonce)
    return concatd_nonce


def compare_headers(req_header_item, resp_header_item):
    req_header_items = str(req_header_item, 'utf-8').split(', ')
    resp_header_items = str(resp_header_item, 'utf-8').split(', ')
    matches = []
    for header in req_header_items:
        if header in resp_header_items:
            matches.append(header)
    if matches:
        return matches


def verify_response(response, nonce):
    global HCONN
    HCONN.receive_data(response)
    response = HCONN.next_event()
    if not response.status_code == 100:
        return response
    try:
        assert response.headers[b'upgrade'] == b'websocket'
    except (KeyError, AssertionError) as e:
        raise NnwsProtocolError('Invalid response on upgrade header')
    try:
        assert response.headers[b'connection'] == b'upgrade'
    except (KeyError, AssertionError) as e:
        raise NnwsProtocolError('Invalid response on connection header')
    try:
        accept_key = response.headers[b'sec-websocket-accept']
        magic_nonce = secondary_nonce_constructor(nonce)
        assert accept_key == magic_nonce
    except (KeyError, AssertionError) as e:
        raise NnwsProtocolError('Invalid response on sec-websocket'
                                '-accept header')
    compare_extensions = None
    try:
        resp_extensions = response.headers[b'sec-websocket-extensions']

        compare_extensions = compare_headers(
            self.req_extensions, str(resp_extensions, 'utf-8'))
        assert compare_extensions
    except KeyError:
        pass
    except AssertionError:
        raise NnwsProtocolError('Invalid extension in response')
    compare_protocols = None
    try:
        resp_protocols = response.headers[b'sec-websocket-protocol']

        compare_protocols = compare_headers(
            self.req_subprotocols, str(resp_protocols, 'utf-8'))
        assert compare_protocols
    except KeyError:
        pass
    except AssertionError:
        raise NnwsProtocolError('Invalid protocol in response')
    return compare_protocols, compare_extensions

'''
conn = Connection(role='CLIENT')
print(conn.next_event())
print(conn.send(Handshake(
    'http://www.iana.org/domains/example/', protocols='theelous3.net/chat', extensions='gzip')))
print(conn.next_event())
print(conn.nonce)
conn.recv(b'HTTP/1.0 302 Found\r\nLocation: http://www.iana.org/domains/example/\r\nServer: BigIP\r\nConnection: Keep-Alive\r\nContent-Length: 0\r\n\r\n')
'''
