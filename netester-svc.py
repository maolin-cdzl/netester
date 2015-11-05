#!/usr/bin/env python
#encoding: utf8 

import os
import time
import signal
import threading
import socket
import select
from service import Listener,Service

g_current_path = os.path.abspath(os.path.dirname(__file__))
shutdown_event = None


def ctrl_c(signum, frame):
    """Catch Ctrl-C key sequence and set a shutdown_event for our threaded
    operations
    """

    print('ctrl_c')
    global shutdown_event
    shutdown_event.set()
#    raise SystemExit('Cancelling...')



class DownStream(Service):
    def __init__(self,sock):
        self.running = True
        self.data = 'a' * 256
        self.start_time = 0.0
        self.send_bytes = 0
        super(DownStream,self).__init__(sock)

    def on_start(self):
        print('DownStream service start')
        self.start_time = time.time()
        self.send_bytes = 0
        super(DownStream,self).on_start()

    def on_stop(self):
        print('DownStream service stop,speed = %fkb/s' % ( self.send_bytes * 8 / 1000 / (time.time() - self.start_time)) )
        super(DownStream,self).on_stop()

    def is_running(self):
        return self.running

    def select(self):
        return (False,True,0)

    def on_writable(self):
        try:
            if 0 == self.sock.sendall(self.data):
                self.running = False
            else:
                self.send_bytes += len(self.data)
        except IOError:
            self.running = False


def main():
    global shutdown_event
    shutdown_event = threading.Event()
    signal.signal(signal.SIGINT, ctrl_c)

    try:
        svc = Listener(('127.0.0.1',59000),DownStream)
        svc.start()

        while not shutdown_event.isSet():
            time.sleep(1)

        print('Service shutdown...')
        svc.stop()
    except KeyboardInterrupt:
        print('\nShutdown...\n')

if __name__ == '__main__':
    main()
