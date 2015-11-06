#!/usr/bin/env python
#encoding: utf8 

import os
import time
import threading
import socket
import select

class Service(object):
    def __init__(self,sock):
        #print('Service init')
        self.sock = sock
        super(Service,self).__init__()

    def is_running(self):
        return True

    def on_start(self):
        pass

    def on_stop(self):
        #print('Service on_stop')
        if self.sock:
            self.sock.close()
            self.sock = None

    # (read? write? timeout?)
    def select(self):
        return (True,False,0)

    def on_readable(self):
        raise NotImplementedError("Please Implement this method")

    def on_writable(self):
        raise NotImplementedError("Please Implement this method")

    def on_timeout(self):
        raise NotImplementedError("Please Implement this method")

class Actor(threading.Thread):
    def __init__(self):
        #print('Actor init')
        self.p0_r = None
        self.p0_w = None
        self.p1_r = None
        self.p1_w = None
        super(Actor,self).__init__()

    def __clean(self):
        if self.p0_w is not None:
            os.close(self.p0_w)
            self.p0_w = None

        if self.p0_r is not None:
            os.close(self.p0_r)
            self.p0_r = None

        if self.p1_w is not None:
            os.close(self.p1_w)
            self.p1_w = None

        if self.p1_r is not None:
            os.close(self.p1_r)
            self.p1_r = None

    def start(self):
        if self.p0_r is not None:
            raise RuntimeError('Actor already running')

        self.p0_r,self.p1_w = os.pipe()
        self.p1_r,self.p0_w = os.pipe()

        super(Actor,self).start()

    def stop(self):
        if self.isAlive():
            #print('Actor send $TERM in stop()')
            os.write(self.p0_w,'$TERM')
            d = os.read(self.p0_r,1024)
        self.__clean()


    def run(self):
        self.routine(self.p1_r,self.p1_w)
    
    def routine(self,pipe_in,pipe_out):
        raise NotImplementedError("Please Implement this method")


class ServiceActor(Actor):
    def __init__(self,svc):
        #print('ServiceActor init')
        self.svc = svc
        super(ServiceActor,self).__init__()

    def routine(self,pipe_in,pipe_out):
        try:
            self.svc.on_start()
            while self.svc.is_running():
                read,write,timeout = self.svc.select()
                inputs = [ pipe_in ]
                outputs = []

                if read:
                    inputs.append(self.svc.sock)
                if write:
                    outputs.append(self.svc.sock)

                readables = None
                writables = None
                excepts = None
                if timeout != 0:
                    readables,writables,excepts = select.select(inputs,outputs,[],timeout)
                    if not (readables or writables or excepts ):
                        self.svc.on_timeout()
                        continue
                else:
                    readables,writables,excepts = select.select(inputs,outputs,[])

                if pipe_in in readables:
                    #print('ServiceActor detect pipe_in readable')
                    d = os.read(pipe_in,1024)
                    break

                if self.svc.sock in readables:
                    self.svc.on_readable()
                if self.svc.sock in writables:
                    self.svc.on_writable()
        finally:
            #print('ServiceActor write $TERM')
            os.write(pipe_out,'$TERM')
            self.svc.on_stop()

class Listener(Actor):
    def __init__(self,address,svcmeta):
        #print('Listener init')
        self.address = address
        self.svcmeta = svcmeta
        self.actors = []
        super(Listener,self).__init__()

    def get_inputs(self,sock,pipe_in):
        inputs = [sock,pipe_in]
        for actor in self.actors:
            inputs.append(actor.p0_r)
        return inputs

    def routine(self,pipe_in,pipe_out):
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind(self.address)
        sock.listen(5)

        running = True

        try:
            while running:
                reads,writes,excepts = select.select(self.get_inputs(sock,pipe_in),[],[])

                for s in reads:
                    if s == sock:
                        conn,addr = sock.accept()
                        actor = ServiceActor(self.svcmeta(conn))
                        actor.start()
                        self.actors.append(actor)
                    elif s == pipe_in:
                        #print('Listener detect pipe_in readable')
                        d = os.read(pipe_in,128)
                        running = False
                        break
                    else:
                        self.handle_actor_exit(s)

            #print('Listern shuting down...')
        finally:
            sock.close()
            for actor in self.actors:
                actor.stop()
            self.actors = []
            os.write(pipe_out,'$TERM')

        #print('Listern shutdown')

    def handle_actor_exit(self,s):
        for actor in self.actors:
            if actor.p0_r == s:
                #print('Listener actor destroy')
                actor.stop()
                self.actors.remove(actor)
                break

def createUdpService(address,svcmeta):
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind(address)

    return ServiceActor(svcmeta(sock))
