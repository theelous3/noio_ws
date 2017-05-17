import tkinter as tk
try:
    from _tkinter import DONT_WAIT
except ImportError:
    DONT_WAIT = 2
import time

import curio
from curio import socket, UniversalQueue, run

import noio_ws as ws


class ClientChat:
    def __init__(self):
        self.coro_ops = UniversalQueue()

        self.root = tk.Tk()
        self.root.bind('<Escape>', self.disconnect)

        self.root.title('noio_ws Test Client')
        self.root.minsize(150, 100)
        self.root['bg'] = '#D9D7BF'

        self.message_area = tk.Text(self.root)
        self.message_area['state'] = 'disabled'
        self.message_area['bg'] = '#D9D7BF'
        self.message_area['fg'] = '#3B3A32'

        self.entry_area = tk.Entry(self.root)
        self.entry_area['relief'] = 'solid'
        self.entry_area['bd'] = 1
        self.entry_area['bg'] = '#D9D7BF'
        self.entry_area['fg'] = '#3B3A32'
        self.entry_area.bind('<Return>', self.callback_sender)

        self.entry_area.pack(side='bottom', fill='x')
        self.message_area.pack(side='left', fill='both', expand=True)

        self.wcon = ws.Connection(role='CLIENT')

    async def tk_mainloop(self, root):
        try:
            dooneevent = root.tk.dooneevent
        except AttributeError:
            # probably running in pypy
            dooneevent = _tkinter.dooneevent
        count = 0
        while True:

            count += 1
            dooneevent(DONT_WAIT)
            await curio.sleep(0)

            # stop if the root window is destroyed
            try:
                root.winfo_exists()
            except tk.TclError:
                break

    async def main(self):
        recv_task = await curio.spawn(self.run())
        await self.tk_mainloop(self.root)
        await recv_task.cancel()

    async def run(self):
        self.sock = curio.socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        await self.sock.connect(('localhost', 25000))
        await curio.spawn(self.get_events())
        while True:
            coro = await self.coro_ops.get()
            await coro

    async def get_events(self):
        while True:
            event = self.wcon.next_event()
            print(event)
            if event is ws.Directive.NEED_DATA:
                self.wcon.recv((await self.sock.recv(4096)))
                continue
            if event == ws.Information.CONNECTION_CLOSED:
                print('we outty')
                self.root.quit()
                self.root.destroy()
                break
            self.message_area['state'] = 'normal'
            self.message_area.insert(tk.INSERT, f'{event.message}\n')
            self.message_area['state'] = 'disabled'
            self.message_area.see("end")

    def callback_sender(self, event):
        msg = self.entry_area.get()
        if msg:
            self.entry_area.delete(0, 'end')
            self.coro_ops.put(self.ws_send(msg, 'text'))

    async def ws_send(self, message, type):
        await self.sock.sendall(self.wcon.send(ws.Data(message, type, True)))

    def disconnect(self, event):
        self.coro_ops.put(self.ws_send('', 'close'))


if __name__ == '__main__':
    app = ClientChat()
    curio.run(app.main())
