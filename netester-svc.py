#!/usr/bin/env python
#encoding: utf8 

import os
import time
import signal
import threading
import socket
import select
import json
from service import Listener,Service,createUdpService

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



class DownloadSpeedService(Service):
    def __init__(self,sock):
        self.running = True
        self.data = ''
        self.starting = False
        self.start_time = 0.0
        self.send_bytes = 0
        super(DownloadSpeedService,self).__init__(sock)

    def on_start(self):
        print('DownloadSpeedService service start')
        super(DownloadSpeedService,self).on_start()

    def on_stop(self):
        print('DownloadSpeedService service stop,speed = %fkb/s' % ( self.send_bytes * 8 / 1000 / (time.time() - self.start_time)) )
        super(DownloadSpeedService,self).on_stop()

    def is_running(self):
        return self.running

    def select(self):
        if self.starting:
            return (False,True,0)
        else:
            return (True,False,0)

    def on_readable(self):
        try:
            d = self.sock.recv(1024)
            if len(d) > 0:
                cmd = json.loads(d)
                block = cmd['block']
                if isinstance(block,int):
                    self.data = bytearray(block)
                    self.start_time = time.time()
                    self.send_bytes = 0
                    self.starting = True
                    return
        except IOError,ValueError:
            self.running = False
            pass

        self.running = False

    def on_writable(self):
        try:
            if 0 == self.sock.sendall(self.data):
                self.running = False
            else:
                self.send_bytes += len(self.data)
        except IOError:
            self.running = False

class UdpEchoService(Service):
    def __init__(self,sock):
        super(UdpEchoService,self).__init__(sock)

    def select(self):
        return (True,False,0)

    def on_readable(self):
        data,addr = self.sock.recvfrom(2048)
        if len(data) > 0 :
            self.sock.sendto(data,addr)

class RtpDownstreamService(Service):
    class RtpDownstreamClient:
        def __init__(self,address,period,size,alive):
            self.address = address
            self.period = period
            self.size = size
            self.alive = alive
            self.delay = 0
            self.seq = 1

    def __init__(self,sock):
        self.nextstep = 0.0
        self.clients = {}
        super(RtpDownstreamService,self).__init__(sock)

    def on_start(self):
        self.nextstep = time.time()
        super(RtpDownstreamService,self).on_start()

    def select(self):
        now = time.time()
        if self.nextstep > now:
            timeout = self.nextstep - now
        else:
            print('Warning: nextstep is smaller than now!')
            timeout = 0.001
        return (True,False,timeout)

    def on_readable(self):
        """ json format:
            { "period" : <how many 20ms>, "size" : <bytes> }
        """

        try:
            data,addr = self.sock.recvfrom(2048)
            conf = json.loads(data)

            if conf.has_key('exit'):
                if self.clients.has_key(addr):
                    del(self.clients[addr])
                return
            period = conf['period']
            size = conf['size']
            if period <= 0 or period >= 500 or size < 12 or size >= 1500:
                return

            if self.clients.has_key(addr):
                client = self.clients[addr]
                client.period = period
                client.size = size
                client.alive = time.time()
            else:
                self.clients[addr] = self.RtpDownstreamClient(addr,period,size,time.time())
        except IOError as e:
            print('error: %s' % e)
            pass


    def on_timeout(self):
        self.nextstep += 0.02
        now = time.time()

        for addr,client in self.clients.items():
            if client.delay <= 1:
                header = ('{\"seq\":%d}' % client.seq)
                packet = bytearray(header)
                packet += bytearray(client.size - len(packet)) # append \0
                self.sock.sendto(packet,addr)
                client.delay = client.period
                client.seq += 1
            else:
                client.delay -= 1

        for k in self.clients.keys():
            if self.clients[k].alive + 30.0 < now:
                del(self.clients[k])

def main():
    global shutdown_event
    shutdown_event = threading.Event()
    signal.signal(signal.SIGINT, ctrl_c)

    svcs = []
    try:
        dssvc = Listener(('127.0.0.1',59000),DownloadSpeedService)
        dssvc.start()
        svcs.append(dssvc)

        echosvc = createUdpService(('127.0.0.1',59001),UdpEchoService)
        echosvc.start()
        svcs.append(echosvc)

        rdssvc = createUdpService(('127.0.0.1',59002),RtpDownstreamService)
        rdssvc.start()
        svcs.append(rdssvc)

        while not shutdown_event.isSet():
            time.sleep(1)

        print('Service shutdown...')
    except KeyboardInterrupt:
        print('\nService Shutdown...\n')
    finally:
        for svc in svcs:
            svc.stop()
        svcs = []

if __name__ == '__main__':
    main()
