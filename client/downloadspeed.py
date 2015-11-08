#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import threading
import socket
import Queue
import json

from speedreport import SpeedReport

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

class DownloadSpeed:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        reports = []
        print('<---DownloadSpeed---')
        for block in self.conf['block']:
            for threads in self.conf['threads']:
                report = self.runonce(block,threads)
                print(json.dumps(report.report()))
                reports.append(report)
        print('---DownloadSpeed--->')

        return reports

    def runonce(self,block,threads):
        workers = []
        report = SpeedReport(block,threads)
        deadline = time.time() + self.conf['period']
        q = Queue.Queue(maxsize=0)
        for i in range(0,threads):
            w = DownloadSpeedWorker(self.address,q,block);
            w.start()
            workers.append(w)

        now = time.time()
        tv_last = now
        report.start()

        try:
            while True:
                try:
                    data_len = q.get(True,1.0)
                    report.receive(data_len)
                except Queue.Empty:
                    pass

                now = time.time()
                if now >= deadline:
                    break
                if now >= tv_last + 1.0:
                    report.period()
                    tv_last = now
                    sys.stdout.write('.')
                    sys.stdout.flush()
        finally:
            report.end()

        for w in workers:
            if w.running:
                w.running = False
        for w in workers:
            if w.isAlive():
                w.join(timeout=0.2)
        workers = []

        sys.stdout.write('\n')
        sys.stdout.flush()
        return report


