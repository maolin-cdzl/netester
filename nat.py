#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import socket
import json

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
            return pubaddr
        except socket.timeout:
            pass
        return None

    def run(self):
        sock = None
        tv = self.conf['min']
        max_tv = self.conf['max']

        nat_valid = 0
        try:
            sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP)
            sock.settimeout(5.0)
            
            while tv < max_tv:
                addr_0 = self.get_pub_addr(sock)
                if addr_0 is None:
                    break
                print('%s:%d' % (addr_0['ip'],addr_0['port']))
                time.sleep(tv)
                addr_1 = self.get_pub_addr(sock)
                if addr_1 is None:
                    break

                print('%s:%d' % (addr_1['ip'],addr_1['port']))
                if addr_1['ip'] != addr_0['ip'] or addr_1['port'] != addr_0['port']:
                    break;
                nat_valid = tv
                tv += 1.0
                time.sleep(0.2)

        finally:
            if sock is not None:
                sock.close()

        print('NAT valid time: %f' % tv)
        return tv
