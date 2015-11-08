#!/usr/bin/env python
#encoding: utf8 

import time

class SpeedReport:
    def __init__(self,block,threads):
        self.block = block
        self.threads = threads
        self.sum_bytes = 0
        self.start_time = 0.0
        self.end_time = 0.0
        self.period_bytes = 0
        self.period_start = 0.0

        self.avg_speed = 0.0
        self.max_speed = 0.0
        self.min_speed = 0.0

    def start(self):
        self.start_time = time.time()
        self.period_start = self.start_time

    def receive(self,data_len):
        self.period_bytes += data_len

    def period(self):
        now = time.time()
        speed = (self.period_bytes / (now - self.period_start)) * 8 / 1000
        self.sum_bytes += self.period_bytes
        if speed > self.max_speed:
            self.max_speed = speed
        if self.min_speed == 0 or speed < self.min_speed:
            self.min_speed = speed
        self.period_start = now
        self.period_bytes = 0

    def end(self):
        self.end_time = time.time()
        self.sum_bytes += self.period_bytes
        self.avg_speed = (self.sum_bytes / (self.end_time - self.start_time)) * 8 / 1000

    def report(self):
        return {
                'block' : self.block,
                'threads' : self.threads,
                'start' : self.start_time,
                'end' : self.end_time,
                'bytes' : self.sum_bytes,
                'max' : self.max_speed,
                'min' : self.min_speed,
                'avg' : self.avg_speed
        }


