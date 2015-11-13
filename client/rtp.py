#!/usr/bin/env python
#encoding: utf8

class RtpStatus:
    def __init__(self,frame_per_packet,frame_bytes,head_bytes):
        self.frame_per_packet = frame_per_packet
        self.frame_bytes = frame_bytes
        self.head_bytes = head_bytes
        self.max_seq = 0
        self.base_seq = 0
        self.bad_seq = 0
        self.probation = 2
        self.received = 0
        self.transit = 0.0
        self.jitter = 0.0
        self.max_jitter = 0.0
    def report(self):
        return {
            'frame_per_packet' : self.frame_per_packet,
            'frame_bytes' : self.frame_bytes,
            'head_bytes' : self.head_bytes,
            'jitter' : self.jitter,
            'max_jitter' : self.max_jitter,
            'received' : self.received,
            'lost' : self.get_lost()
        }

    def get_lost(self):
        if self.received > 0:
            expected = self.max_seq - self.base_seq + 1
            return float(expected - self.received) / float(expected)
        else:
            return 1.0

    def init_seq(self,seq):
        self.base_seq = seq
        self.max_seq = seq
        self.bad_seq = 100000
        self.received = 0

    def update_seq(self,seq):
        udelta = abs(seq - self.max_seq)

        if self.probation > 0:
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
