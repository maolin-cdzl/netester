#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import socket
import json

from rtp import RtpStatus

class RtpDownloadStream:
    def __init__(self,server,conf):
        self.address = (server,conf['port'])
        self.conf = conf

    def run(self):
        reports = []
        for frame_count in self.conf['frame_per_packet']:
            for frame_bytes in self.conf['frame_bytes']:
                packet_bytes = frame_count * frame_bytes + self.conf['rtp_head']
                s = self.runonce(frame_count,packet_bytes)
                report = ('[FramePerPacket:%d,FrameBytes:%d] - Jitter:%f MaxJitter:%f Lost:%f' % (frame_count,frame_bytes,s.jitter,s.max_jitter,s.get_lost()))
                print(report)
                reports.append(report)
        return reports

    def runonce(self,frame_count,packet_bytes):
        s = RtpStatus()
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.settimeout(5.0)

        cmd = json.dumps({ 'period' : frame_count, 'size' : packet_bytes })
        sock.sendto(cmd,self.address)
        
        now = time.time()
        deadline = now + self.conf['period']
        start_time = now - 100.0

        try:
            data,addr = sock.recvfrom(2048)
            now = time.time()
            data = data.strip('\0')
            seq = json.loads(data)['seq']
            ts = seq * frame_count * 0.02

            s.init_seq(seq)
            s.max_seq = seq - 1
            s.probation = 2

            s.update_seq(seq)
            s.transit = (now - start_time) - ts
        except IOError as e:
            print('IOError: %s' % e)
            return s
            
        
        while now < deadline:
            try:
                data,addr = sock.recvfrom(2048)
                now = time.time()
                data = data.strip('\0')
                seq = json.loads(data)['seq']
                ts = seq * frame_count * 0.02

                if s.update_seq(seq):
                    # calc jitter
                    transit = (now - start_time )- ts
                    d = abs(transit - s.transit)
                    s.transit = transit
                    s.jitter += (1.0 / 16.0) * ( d - s.jitter )
                    if s.jitter > s.max_jitter:
                        s.max_jitter = s.jitter
            except socket.timeout as e:
                pass

        sock.sendto('{\"exit\":1}',self.address)
        time.sleep(0.1)
        sock.close()
        return s


    

