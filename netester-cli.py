#!/usr/bin/env python
#encoding: utf8 

import os
import time
import Queue
import StringIO
import threading
import socket

import netester_pb2 as protocol
import pb

current_path = os.path.abspath(os.path.dirname(__file__))


def get_timestamp():
    return int(round(time.time() * 1000.0));


class DownStream(threading.Thread):
    """A download stream thread"""

    def __init__(self,addr,q,e):
        self.address = addr
        self.q = q
        self.e = e
        threading.Thread.__init__(self);

    def recv_data(self,s):
        return len(s.recv(1024))

    def run(self):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        last_report = time.time()
        last_bytes = 0
        now = 0
        try:
            s.connect(self.address)
            while not self.e.isSet():
                datalen = self.recv_data(s)
                if 0 == datalen:
                    break
                last_bytes += datalen
                now = time.time()

                if now - last_report >= 0.5:
                    print('\t%d, Speed %fkb/s\n' % ( last_bytes, last_bytes * 8 / 1000 / (now - last_report) ))
                    self.q.put(last_bytes,True)
                    last_bytes = 0
                    last_report = now
        except IOError:
            print('Socket IOError')
            pass
        s.close()
        self.q.put(0)

    def get_speed(self):
        tv = float(self.end_time - self.start_time)
        if tv > 0 and self.recv_bytes > 0:
            return float(self.recv_bytes) / ( tv / 1000.0 )
        else:
            return float(0)
        
def downloadSpeed(addr,tcount,timeout):
    workers = []
    deadline = time.time() + timeout
    q = Queue.Queue(maxsize=0)
    stop_event = threading.Event()
    for i in range(0,tcount):
        w = DownStream(addr,q,stop_event);
        w.start()
        workers.append(w)

    bytes_sum = 0
    tv_start = time.time()
    maxspeed = 0.0
    minspeed = 0.0
    avgspeed = 0.0
    tv_update = tv_start

    tv_last = tv_start
    bytes_last = 0
    speed = 0.0
    now = 0

    while 1:
        try:
            bytes_last += q.get(True,1)
        except Queue.Empty:
            pass
        now = time.time()
        if now >= deadline:
            break
        if now >= tv_last + 1.0:
            speed = ( bytes_last / (now - tv_last)) 
            print('bytes_last %d, speed %f' % (bytes_last,speed))
            bytes_sum += bytes_last
            tv_last = now
            bytes_last = 0

            updated = False
            avgspeed_tmp = ( bytes_sum / (now - tv_start))
            if abs(avgspeed_tmp - avgspeed) > 1000.0:
                updated = True
            avgspeed = avgspeed_tmp

            if speed > maxspeed:
                maxspeed = speed
                updated = True

            if speed < minspeed or (minspeed == 0.0 and speed > 0 ) :
                minspeed = speed
                updated = True


            if updated:
                tv_update = now
            else:
                if now - tv_update >= 3.0:
                    break

    stop_event.set()
    for w in workers:
        if w.isAlive():
            w.join(timeout=0.2)

    avgspeed = avgspeed * 8.0;
    maxspeed = maxspeed * 8.0;
    minspeed = minspeed * 8.0;

    return (avgspeed,maxspeed,minspeed)


address = ('127.0.0.1',59000)
avgspeed,maxspeed,minspeed = downloadSpeed(address,1,10)

print('avg %fkb/s, max %fkb/s, min %fkb/s' % (avgspeed / 1000,maxspeed / 1000,minspeed / 1000))

