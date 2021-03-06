from urllib.parse import urlparse, urlunparse
from random import randint, getrandbits
from base64 import b64encode, b64decode
from hashlib import sha1
from collections import OrderedDict

import h11
import noio_ws as ws

from .constants import *
from .errors import NnwsProtocolError

__all__ = ['Handshake']


def nonce_creator():
    return b64encode(bytearray([randint(0, 255) for _ in range(1, 17)]))


def secondary_nonce_creator(nonce):
    concatd_nonce = str(nonce, 'utf-8') + MAGIC_STR
    concatd_nonce = sha1(concatd_nonce.encode('utf-8')).digest()
    concatd_nonce = b64encode(concatd_nonce)
    return concatd_nonce


class Handshake:
    def __init__(self, role):
        if role == 'CLIENT':
            self.role = Roles.CLIENT
        elif role == 'SERVER':
            self.role = Roles.SERVER
        else:
            raise AttributeError(role, 'is not a valid role.')
        if self.role is ws.Roles.CLIENT:
            self.hcon = h11.Connection(our_role=h11.CLIENT)
        elif self.role is ws.Roles.SERVER:
            self.hcon = h11.Connection(our_role=h11.SERVER)

        self.nonce = None

    def client_handshake(self, uri, *,
                         subprotocols=None,
                         extensions=None,
                         **kwargs):

        scheme, netloc, path, _, _, _ = urlparse(uri)
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
        self.nonce = nonce_creator()
        headers = {'host': ':'.join((netloc, port)),
                   'upgrade': 'websocket',
                   'connection': 'upgrade',
                   'sec-websocket-key': self.nonce,
                   'sec-websocket-version': '13'}
        if subprotocols is not None:
            headers['sec-websocket-protocol'] = self._addon_header_str_ifier(
                subprotocols)
        if extensions is not None:
            headers['sec-websocket-extensions'] = self._addon_header_str_ifier(
                extensions)
        if kwargs:
            headers.update(kwargs)

        handshake = h11.Request(
            method='GET', target=request_uri, headers=headers.items())

        return handshake

    def verify_response(self, response):
        headers = self.normalise_headers(dict(response.headers))
        if not int(response.status_code) == 101:
            return False, response, None
        try:
            assert headers['upgrade'].lower() == 'websocket'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid response on upgrade header')
        try:
            assert headers['connection'].lower() == 'upgrade'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid response on connection header')
        try:
            accept_key = headers['sec-websocket-accept']
            magic_nonce = secondary_nonce_creator(self.nonce)
            assert bytes(accept_key, 'utf-8') == magic_nonce
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid response on sec-websocket'
                                    '-accept header')

        return self._parse_response_for_addons(response)

    def verify_request(self, request):
        headers = self.normalise_headers(dict(request.headers))
        try:
            assert headers['upgrade'] == 'websocket'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid request on upgrade header')
        try:
            assert headers['connection'] == 'upgrade'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid request on connection header')
        try:
            self.nonce = headers['sec-websocket-key']
            assert len(b64decode(str(self.nonce, 'utf-8'))) == 16
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Bad nonce from client')
        try:
            assert headers['sec-websocket-version'] == '13'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Bad version from client')

        return self._parse_response_for_addons(request)

    def server_handshake(self,
                         subprotocols=None,
                         extensions=None,
                         **kwargs):
        headers = {'upgrade': 'websocket',
                   'connection': 'upgrade',
                   'sec-websocket-accept': secondary_nonce_creator(self.nonce),
                   'sec-websocket-version': '13'}
        if subprotocols:
            headers['sec-websocket-protocol'] = self._addon_header_str_ifier(
                self.subprotocols)
        if extensions:
            headers['sec-websocket-extensions'] = self._addon_header_str_ifier(
                self.extensions)
        if kwargs:
            headers.update(kwargs)
        return h11.InformationalResponse(
            status_code=101, reason='Switching Protocols',
            headers=headers.items())

    def _parse_response_for_addons(self, response_obj):
        extension_headers = []
        subprotocol_headers = []
        for header in response_obj.headers:
            if header[0] == 'sec-websocket-extensions':
                extension_headers.append(header[1].decode('utf-8'))
            elif header[0] == 'sec-websocket-protocols':
                subprotocol_headers.append(header[1].decode('utf-8'))

        extensions = self._parse_addon_header(','.join(extension_headers))
        protocols = self._parse_addon_header(','.join(subprotocol_headers))

        return extensions, protocols

    def _parse_addon_header(self, header):
        all_vals = header.replace(', ', ',').split(',')
        results = OrderedDict()
        for item in all_vals:
            sub_val = item.split(';')
            val_details = {}
            name, *params = sub_val
            if params:
                for param in params:
                    arg, value = param.strip().split('=')
                    try:
                        val_details[arg] = value
                    except IndexError:
                        val_details[arg] = None
            results[name] = val_details
        return results

    def _addon_header_str_ifier(self, header_items):
        assert isinstance(header_items, OrderedDict)
        header_fields = []
        for item in header_items:
            header_holding = []
            header_holding.append(item.pop('name'))
            if item:
                for k, v in item.items():
                    header_holding.append('='.join([k, v]))
            header_fields.append(';'.join(header_holding))
        return ', '.join(header_fields)

    def normalise_headers(self, headers):
        normalised_headers = {}
        for k, v in headers.items():
            try:
                normalised_headers[k.decode('utf-8').lower()] = \
                    v.decode('utf-8')
            except AttributeError:
                normalised_headers[k.lower()] = v.decode()
        return normalised_headers


def mask_unmask(data, mask):
    for i, x in enumerate(data):
        data[i] = x ^ mask[i % 4]
    return data
