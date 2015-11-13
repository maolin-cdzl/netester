#!/usr/bin/env python
#encoding: utf8

import os
import sys
import time
import socket
import json

IP_MTU_DISCOVER   = 10
IP_PMTUDISC_DONT  =  0  # Never send DF frames.
IP_PMTUDISC_WANT  =  1  # Use per route hints.
IP_PMTUDISC_DO    =  2  # Always DF.
IP_PMTUDISC_PROBE =  3  # Ignore dst pmtu.

class MtuReport:
    def __init__(self):
        self.mtu = 0

    def report(self):
        return {'mtu' : self.mtu}

class Mtu:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def try_mtu(self,sock,mtu):
        packet = bytearray(mtu)
        try:
            re = sock.sendto(packet,self.address)
            if re != mtu:
                return False
        except socket.error:
            return False

        try:
            ack,addr = sock.recvfrom(max(mtu,2048))
            if len(ack) == mtu:
                return True
            else:
                return
        except socket.timeout:
            pass

        return False

    def run(self):
        sock = None
        min_v = self.conf['min']
        max_v = self.conf['max']
        mtu = min_v
        report = MtuReport()
        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
            sock.settimeout(5.0)
            #C code:
            #int val = IP_PMTUDISC_DO;      // 2
	    #setsockopt(s, IPPROTO_IP, IP_MTU_DISCOVER, &val, sizeof(val));

            val = sock.getsockopt(socket.SOL_IP,IP_MTU_DISCOVER)
            sock.setsockopt(socket.SOL_IP,IP_MTU_DISCOVER,IP_PMTUDISC_DO)

            while min_v < max_v - 1:
                if self.try_mtu(sock,mtu):
                    min_v = mtu
                    report.mtu = max(report.mtu,mtu)
                else:
                    max_v = mtu
                mtu = int(round( (min_v + max_v) / 2 ))
                time.sleep(0.2)

        finally:
            if sock is not None:
                sock.close()

        print(json.dumps(report.report()))
        return report
