#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import threading
import socket
import Queue
import json

class DownloadSpeedWorker(threading.Thread):
    """A download stream thread"""

    def __init__(self,addr,q,block):
        self.address = addr
        self.queue = q
        self.running = False
        self.cmd = { 'block' : block }
        threading.Thread.__init__(self);

    def recv_data(self,s):
        return len(s.recv(1024))

    def run(self):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect(self.address)
            s.sendall(json.dumps(self.cmd))
        except IOError:
            s.close()
            return

        self.running = True
        try:
            while self.running:
                datalen = 0
                try:
                    datalen = self.recv_data(s)
                except socket.timeout:
                    continue

                if 0 == datalen:
                    break
                else:
                    self.queue.put(datalen,True)
        except IOError:
            print('Socket IOError')
            return
        finally:
            s.close()
            self.running = False

class DownloadSpeedCli:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        best_avg = 0.0
        best_block = 0
        best_threads = 0


        for block in self.conf['block']:
            for threads in self.conf['threads']:
                avgspeed,maxspeed,minspeed = self.runonce(block,threads)
                if avgspeed > best_avg:
                    best_avg = avgspeed
                    best_block = block
                    best_threads = threads
                print('[Block:%d,Threads:%d] avg %fKbps, max %fKbps, min %fKbps' % (block,threads,avgspeed,maxspeed,minspeed))

        return (best_avg,best_block,best_threads)

    def runonce(self,block,tcount):
        workers = []
        deadline = time.time() + self.conf['period']
        q = Queue.Queue(maxsize=0)
        for i in range(0,tcount):
            w = DownloadSpeedWorker(self.address,q,block);
            w.start()
            workers.append(w)

        bytes_sum = 0
        tv_start = time.time()
        maxspeed = 0.0
        minspeed = 0.0
        avgspeed = 0.0

        tv_last = tv_start
        bytes_last = 0
        speed = 0.0
        now = 0

        while 1:
            try:
                bytes_last += q.get(True,1.0)
            except Queue.Empty:
                pass

            now = time.time()
            if now >= deadline:
                break
            if now >= tv_last + 1.0:
                sys.stdout.write('.')
                sys.stdout.flush()

                speed = ( bytes_last / (now - tv_last)) 
                #print('bytes_last %d, speed %f' % (bytes_last,speed))
                bytes_sum += bytes_last
                tv_last = now
                bytes_last = 0

                avgspeed = ( bytes_sum / (now - tv_start))

                if speed > maxspeed:
                    maxspeed = speed

                if speed < minspeed or (minspeed == 0.0 and speed > 0 ) :
                    minspeed = speed

        for w in workers:
            if w.running:
                w.running = False
        for w in workers:
            if w.isAlive():
                w.join(timeout=0.2)
        workers = []

        avgspeed = avgspeed * 8.0 / 1000;
        maxspeed = maxspeed * 8.0 / 1000;
        minspeed = minspeed * 8.0 / 1000;

        sys.stdout.write('\n')
        sys.stdout.flush()
        return (avgspeed,maxspeed,minspeed)


