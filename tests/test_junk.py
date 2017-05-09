#
import noio_ws.constants
from noio_ws.noio_ws import Data, Recvr
data = Data('hello ', 'text', True)
data = data()
data_c = Data('PING BODY', 'ping', True)
data_c = data_c()
data2 = Data('world', 'continuation', True)
data2 = data2()
rvr = Recvr()
r = rvr(data[0])
vars(r)
r = rvr(data_c[0])
vars(r)
r = rvr(data2[0])
vars(r)



import noio_ws as ws

wcon_c = ws.Connection(role='CLIENT')
a = wcon_c.send(ws.Data('HELLO serveadwaadwaddwwdr', 'text', True))


wcon_s = ws.Connection(role='SERVER')
wcon_s.recv(a)
b = wcon_s.next_event()
print(b.message)
