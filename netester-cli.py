#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import Queue
import StringIO
import threading
import socket
import json

current_path = os.path.abspath(os.path.dirname(__file__))


def get_timestamp():
    return int(round(time.time() * 1000.0));


class DownloadSpeed(threading.Thread):
    """A download stream thread"""

    def __init__(self,addr,q,e,block):
        self.address = addr
        self.q = q
        self.e = e
        self.cmd = { 'block' : block }
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
            s.sendall(json.dumps(self.cmd))
            while not self.e.isSet():
                datalen = self.recv_data(s)
                if 0 == datalen:
                    break
                last_bytes += datalen
                now = time.time()

                if now - last_report >= 0.05:
                    #print('\t%d, Speed %fkb/s\n' % ( last_bytes, last_bytes * 8 / 1000 / (now - last_report) ))
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
        
def downloadSpeedRound(addr,block,tcount,timeout):
    workers = []
    deadline = time.time() + timeout
    q = Queue.Queue(maxsize=0)
    stop_event = threading.Event()
    for i in range(0,tcount):
        w = DownloadSpeed(addr,q,stop_event,block);
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

            updated = False
            avgspeed = ( bytes_sum / (now - tv_start))

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

    avgspeed = avgspeed * 8.0 / 1000;
    maxspeed = maxspeed * 8.0 / 1000;
    minspeed = minspeed * 8.0 / 1000;

    sys.stdout.write('\n')
    sys.stdout.flush()
    return (avgspeed,maxspeed,minspeed)


def getDownloadSpeed(server,conf):
    best_avg = 0.0
    best_block = 0
    best_threads = 0

    address = (server,conf['port'])

    for block in conf['block']:
        for threads in conf['threads']:
            avgspeed,maxspeed,minspeed = downloadSpeedRound(address,block,threads,10)
            if avgspeed > best_avg:
                best_avg = avgspeed
                best_block = block
                best_threads = threads
            print('[Block:%d,Threads:%d] avg %fkb/s, max %fkb/s, min %fkb/s' % (block,threads,avgspeed,maxspeed,minspeed))

    return (best_avg,best_block,best_threads)

class RtpStatus:
    def __init__(self):
        self.max_seq = 0
        self.base_seq = 0
        self.bad_seq = 0
        self.probation = 2
        self.received = 0
        self.transit = 0.0
        self.jitter = 0.0

    def get_lost(self):
        if self.received > 0:
            expected = self.max_seq - self.base_seq + 1
            return float(expected - self.received) / float(expected)
        else:
            return 0.0

    def init_seq(self,seq):
        self.base_seq = seq
        self.max_seq = seq
        self.bad_seq = 100000
        self.received = 0

    def update_seq(self,seq):
        udelta = abs(seq - self.max_seq)

        if self.probation:
            if seq == self.max_seq + 1:
                self.probation -= 1
                self.max_seq = seq
                if self.probation == 0:
                    self.init_seq(seq)
                    self.received += 1
                    return True
            else:
                self.probation = 1
                self.max_seq = seq
                return False
        elif udelta == 0:
            # duplicate
            return False
        elif udelta < 3000:
            self.max_seq = seq
        else:
           # the sequence number made a very large jump
           if seq == self.bad_seq:
               # Two sequential packets -- assume that the other side
               # restarted without telling us so just re-sync
               # (i.e., pretend this was the first packet).
               init_seq(s, seq);
           else:
               self.bad_seq = seq + 1
               return False
        self.received += 1
        return True

def rtpDownloadStreamRound(address,timeout,frame_count,packet_bytes):
    s = RtpStatus()
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.settimeout(5.0)

    cmd = json.dumps({ 'period' : frame_count, 'size' : packet_bytes })
    sock.sendto(cmd,address)
    
    now = time.time()
    deadline = now + timeout
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
        except socket.timeout as e:
            pass

    sock.sendto('{\"exit\":1}',address)
    time.sleep(0.1)
    sock.close()
    return s


def rtpDownloadStream(server,conf):
    address = (server,conf['port'])

    for frame_count in conf['frame_per_packet']:
        for frame_bytes in conf['frame_bytes']:
            packet_bytes = frame_count * frame_bytes + conf['rtp_head']
            s = rtpDownloadStreamRound(address,10,frame_count,packet_bytes)
            print('[FramePerPacket:%d,FrameBytes:%d] - Jitter:%f lost:%f' % (frame_count,frame_bytes,s.jitter,s.get_lost()))
    


def main():
    conf = json.load(file('%s/netester-cli.json' % current_path))
    server = conf['server']

    #speed,block,threads = getDownloadSpeed(server,conf['DownloadSpeed'])
    #print('Speed = %f, block = %d, threads = %d' % (speed,block,threads))

    rtpDownloadStream(server,conf['RtpDownload'])

if __name__ == '__main__':
    main()
