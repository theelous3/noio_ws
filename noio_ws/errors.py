all = ['NnwsBaseError', 'NnwsProtocolError']


class NnwsBaseError(Exception):
    pass


class NnwsProtocolError(NnwsBaseError):
    pass
