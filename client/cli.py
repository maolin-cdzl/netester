#!/usr/bin/env python
#encoding: utf8

import os
import sys
import time
import Queue
import threading
import socket
import json

from downloadspeed import DownloadSpeed
from uploadspeed import UploadSpeed
from rtpdownstream import RtpDownStream
from delay import UdpDelay,TcpDelay
from mtu import Mtu
from nat import Nat

def we_are_frozen():
    return hasattr(sys,'frozen')
def module_path():
    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable,sys.getfilesystemencoding()))
    else:
        return os.path.dirname(unicode(__file__, sys.getfilesystemencoding( )))

current_path = os.path.abspath(os.path.dirname(module_path()))


def get_timestamp():
    return int(round(time.time() * 1000.0));

def main():
    conf = json.load(file('%s/conf.json' % current_path))
    server = conf['server']
    #server = '127.0.0.1'
    print('Test from server: %s' % server)

    tester = Mtu(server,conf['MTU'])
    tester.run()

    tester = Nat(server,conf['NAT'])
    tester.run()

    tester = DownloadSpeed(server,conf['DownloadSpeed'])
    tester.run()

    tester = UploadSpeed(server,conf['UploadSpeed'])
    tester.run()

    tester = RtpDownStream(server,conf['RtpDownStream'])
    tester.run()

    tester = UdpDelay(server,conf['UdpDelay'])
    tester.run()

    tester = TcpDelay(server,conf['TcpDelay'])
    tester.run()


if __name__ == '__main__':
    main()