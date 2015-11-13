#!/usr/bin/env python
#encoding: utf8

import os
import sys
import time
import socket
import json

class NatReport:
    def __init__(self):
        self.alive = 0
        self.ip = ''
        self.port = 0
    def report(self):
        return {'alive' : self.alive, 'ip': self.ip, 'port': self.port}

class Nat:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def get_pub_addr(self,sock):
        packet = bytearray(10)
        sock.sendto(packet,self.address)

        try:
            ack,addr = sock.recvfrom(2048)
            pubaddr = json.loads(ack)
            return (pubaddr['ip'],pubaddr['port'])
        except socket.timeout:
            pass
        return ('',0)

    def run(self):
        sock = None
        tv = self.conf['min']
        max_tv = self.conf['max']
        report = NatReport()

        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
            sock.settimeout(5.0)

            report.ip,report.port = self.get_pub_addr(sock)
            if len(report.ip) > 0:
                while tv < max_tv:
                    time.sleep(tv)
                    ip,port = self.get_pub_addr(sock)
                    if len(ip) == 0:
                        break

                    if ip != report.ip or port != report.port:
                        break;
                    report.alive = tv
                    tv += 1.0
                    time.sleep(0.2)

        finally:
            if sock is not None:
                sock.close()

        print(json.dumps(report.report()))
        return report
