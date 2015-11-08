#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import socket
import json

class UdpDelayReport:
    def __init__(self,bandwidth,packetbytes):
        self.bandwidth = bandwidth
        self.packetbytes = packetbytes
        self.avg_delay = 0.0
        self.max_delay = 0.0
        self.min_delay = 0.0
        self.received = 0
        self.lost = 0

    def record(self,delay):
        if delay > self.max_delay:
            self.max_delay = delay
        if self.min_delay == 0 or delay < self.min_delay:
            self.min_delay = delay
        self.avg_delay = ((self.avg_delay * self.received) + delay) / (self.received + 1)
        self.received += 1

    def addLost(self):
        self.lost += 1

    def report(self):
        return { 
                'bandwidth' : self.bandwidth, 
                'packet' : self.packetbytes, 
                'received' : self.received,
                'lost' : self.lost,
                'avg_delay' : round(self.avg_delay,4),
                'max_delay' : round(self.max_delay,4),
                'min_delay' : round(self.min_delay,4)
                }

class UdpDelay:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        reports = []
        overhead = self.conf['overhead']
        print('<---UdpDelay---')
        for frame_per_packet in self.conf['frame_per_packet']:
            for frame_bytes in self.conf['frame_bytes']:
                for bandwidth in self.conf['bandwidth']:
                    packet_bytes = (frame_per_packet * frame_bytes) + overhead
                    report = self.runonce(bandwidth,packet_bytes)
                    print( json.dumps(report.report()) )
                    reports.append(report)
        print('---UdpDelay--->')

        return reports

    def runonce(self,bandwidth,size):
        report = UdpDelayReport(bandwidth,size)
        last_send = 0.0
        sock = None
        packet = bytearray(size)
        interval = 1.0 / ((float(bandwidth) * 1000 / 8) / size)

        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            now = time.time()
            deadline = now + self.conf['period']

            while now < deadline:
                try:
                    last_send = time.time()
                    sock.sendto(packet,self.address)
                    rep,addr = sock.recvfrom(2048)

                    now = time.time()
                    delay = now - last_send
                    report.record(delay)

                    d = interval - (now - last_send)
                    if d > 0:
                        time.sleep(d)
                        now = time.time()
                except socket.timeout:
                    report.addLost()
                    now = time.time()
                    pass
        finally:
            if sock is not None:
                sock.close()

        return report

class TcpDelayReport:
    def __init__(self,bandwidth,packetbytes):
        self.bandwidth = bandwidth
        self.packetbytes = packetbytes
        self.avg_delay = 0.0
        self.max_delay = 0.0
        self.min_delay = 0.0
        self.received = 0

    def record(self,delay):
        if delay > self.max_delay:
            self.max_delay = delay
        if self.min_delay == 0 or delay < self.min_delay:
            self.min_delay = delay
        self.avg_delay = ((self.avg_delay * self.received) + delay) / (self.received + 1)
        self.received += 1

    def report(self):
        return { 
                'bandwidth' : self.bandwidth, 
                'packet' : self.packetbytes, 
                'received' : self.received,
                'avg_delay' : round(self.avg_delay,4),
                'max_delay' : round(self.max_delay,4),
                'min_delay' : round(self.min_delay,4)
                }

class TcpDelay:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        reports = []
        overhead = self.conf['overhead']
        print('<---TcpDelay---')
        for frame_per_packet in self.conf['frame_per_packet']:
            for frame_bytes in self.conf['frame_bytes']:
                for bandwidth in self.conf['bandwidth']:
                    packet_bytes = (frame_per_packet * frame_bytes) + overhead
                    report = self.runonce(bandwidth,packet_bytes)
                    print( json.dumps(report.report()) )
                    reports.append(report)
        print('---TcpDelay--->')
        return reports

    def runonce(self,bandwidth,size):
        report = TcpDelayReport(bandwidth,size)
        last_send = 0.0
        sock = None
        packet = bytearray(size)
        interval = 1.0 / ((float(bandwidth) * 1000 / 8) / size)

        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(self.address)

            now = time.time()
            deadline = now + self.conf['period']

            while now < deadline:
                sock.sendall(packet)
                last_send = time.time()
                if len(sock.recv(2048)) == 0:
                    break

                now = time.time()
                delay = now - last_send
                report.record(delay)

                d = interval - (now - last_send)
                if d > 0:
                    time.sleep(d)
                    now = time.time()
        finally:
            if sock is not None:
                sock.close()
        return report
