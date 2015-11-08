#!/usr/bin/env python
#encoding: utf8 

import os
import sys
import time
import Queue
import threading
import socket
import json

from downloadspeed import DownloadSpeedCli
from rtpdownload import RtpDownStream
from delay import UdpDelay,TcpDelay

current_path = os.path.abspath(os.path.dirname(__file__))


def get_timestamp():
    return int(round(time.time() * 1000.0));




def main():
    conf = json.load(file('%s/netester-cli.json' % current_path))
    #server = conf['server']
    server = '127.0.0.1'

    app = DownloadSpeedCli(server,conf['DownloadSpeed'])
    speed,block,threads = app.run()
    print('Speed = %f, block = %d, threads = %d' % (speed,block,threads))

    app = RtpDownStream(server,conf['RtpDownStream'])
    app.run()

    app = UdpDelay(server,conf['UdpDelay'])
    app.run()

    app = TcpDelay(server,conf['TcpDelay'])
    app.run()

if __name__ == '__main__':
    main()
