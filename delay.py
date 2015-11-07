#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import socket
import json

class UdpDelay:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        reports = []
        for packet_bytes in self.conf['packet_bytes']:
            delay,max_delay,min_delay,lost = self.runonce(packet_bytes)
            report = ('[PacketBytes:%d] Avg=%f Max=%f Min=%f Lost=%d' % (packet_bytes,delay,max_delay,min_delay,lost))
            print(report)
            reports.append(report)

        return reports

    def runonce(self,size):
        last_send = 0.0
        max_delay = 0.0
        min_delay = 10.0
        total_time = 0.0
        received = 0
        lost = 0
        sock = None

        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            now = time.time()
            deadline = now + self.conf['period']
            packet = bytearray(size)

            while now < deadline:
                try:
                    sock.sendto(packet,self.address)
                    last_send = time.time()
                    rep,addr = sock.recvfrom(2048)

                    now = time.time()
                    delay = now - last_send
                    received += 1
                    total_time += delay
                    if delay > max_delay:
                        max_delay = delay
                    if delay < min_delay:
                        min_delay = delay
                except socket.timeout:
                    lost += 1
                    pass
        finally:
            if sock is not None:
                sock.close()

        delay = 0
        if received > 0:
            delay = total_time / received
        return (delay,max_delay,min_delay,lost)

class TcpDelay:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        reports = []
        for packet_bytes in self.conf['packet_bytes']:
            delay,max_delay,min_delay = self.runonce(packet_bytes)
            report = ('[PacketBytes:%d] Avg=%f Max=%f Min=%f' % (packet_bytes,delay,max_delay,min_delay))
            print(report)
            reports.append(report)
        return reports

    def runonce(self,size):
        last_send = 0.0
        max_delay = 0.0
        min_delay = 10.0
        total_time = 0.0
        received = 0
        sock = None

        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(self.address)

            now = time.time()
            deadline = now + self.conf['period']
            packet = bytearray(size)

            while now < deadline:
                sock.sendall(packet)
                last_send = time.time()
                if len(sock.recv(2048)) == 0:
                    break

                now = time.time()
                delay = now - last_send
                received += 1
                total_time += delay
                if delay > max_delay:
                    max_delay = delay
                if delay < min_delay:
                    min_delay = delay
        finally:
            if sock is not None:
                sock.close()

        delay = 0
        if received > 0:
            delay = total_time / received
        return (delay,max_delay,min_delay)
