
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
        return matches[0]


class Handshake:
    def __init__(self, wcon):
        self.nonce = None
        self.wcon = wcon

    def client_handshake(uri, **kwargs):
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
        self.nonce = initial_nonce_constructor()
        headers = {'host': ':'.join((netloc, port)),
                   'upgrade': 'websocket',
                   'connection': 'upgrade',
                   'sec-websocket-key': self.nonce,
                   'sec-websocket-version': '13'}
        if self.wcon.protocols:
            headers.update({'sec-websocket-protocol': self.wcon.protocols})
        if self.wcon.extensions:
            headers.update({'sec-websocket-extensions': self.wcon.extensions})
        if kwargs:
            headers.update(kwargs)
        handshake = h11.Request(
            method='GET', target=request_uri, headers=headers.items())
        return handshake

    def verify_response(response):
        if not response.status_code == 101:
            return False, response, None
        try:
            assert response.headers[b'upgrade'] == b'websocket'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid response on upgrade header')
        try:
            assert response.headers[b'connection'] == b'upgrade'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid response on connection header')
        try:
            accept_key = response.headers[b'sec-websocket-accept']
            magic_nonce = secondary_nonce_constructor(self.nonce)
            assert accept_key == magic_nonce
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid response on sec-websocket'
                                    '-accept header')

        compare_extensions = None
        try:
            resp_extensions = response.headers[b'sec-websocket-extensions']

            compare_extensions = compare_headers(
                self.wcon.req_extensions, str(resp_extensions, 'utf-8'))
            assert compare_extensions
        except KeyError:
            pass
        except AssertionError:
            raise NnwsProtocolError('Invalid extension in response')

        compare_protocols = None
        try:
            resp_protocols = response.headers[b'sec-websocket-protocol']

            compare_protocols = compare_headers(
                self.wcon.req_subprotocols, str(resp_protocols, 'utf-8'))
            assert compare_protocols
        except KeyError:
            pass
        except AssertionError:
            raise NnwsProtocolError('Invalid protocol in response')
        return True, compare_protocols, compare_extensions

    def verify_request(request):
        try:
            assert request.headers[b'upgrade'] == b'websocket'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid request on upgrade header')
        try:
            assert request.headers[b'connection'] == b'upgrade'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Invalid request on connection header')
        try:
            self.nonce = request.headers[b'sec-websocket-key']
            assert len(b64decode(str(self.nonce, 'utf-8'))) == 16
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Bad nonce from client')

        compare_extensions = None
        try:
            resp_extensions = request.headers[b'sec-websocket-extensions']
            compare_extensions = compare_headers(
                wcon.extensions, str(resp_extensions, 'utf-8'))
            assert compare_extensions
        except KeyError:
            pass
        except AssertionError:
            raise NnwsProtocolError('Invalid extension in request')

        compare_protocols = None
        try:
            resp_protocols = response.headers[b'sec-websocket-protocol']
            compare_protocols = compare_headers(
                wcon.subprotocols, str(resp_protocols, 'utf-8'))
            assert compare_protocols
        except KeyError:
            pass
        except AssertionError:
            raise NnwsProtocolError('Invalid protocol in response')

        try:
            assert request.headers[b'sec-websocket-version'] == b'13'
        except (KeyError, AssertionError):
            raise NnwsProtocolError('Bad version from client')
        return request

    def server_handshake(**kwargs):
        headers = {'upgrade': 'websocket',
                   'connection': 'upgrade',
                   'sec-websocket-accept': secondary_nonce_constructor(self.nonce),
                   'sec-websocket-version': '13'}
        if self.wcon.protocols:
            headers.update({'sec-websocket-protocol': self.wcon.protocols})
        if self.wcon.extensions:
            headers.update({'sec-websocket-extensions': self.wcon.extensions})
        if kwargs:
            headers.update(kwargs)
        byteball = HCONN.send(h11.InformationalResponse(
            status_code=101, reason='Switching Protocols',
            headers=headers.items()))
        self.wcon.hcon.send(h11.EndOfMessage())
        return byteball
