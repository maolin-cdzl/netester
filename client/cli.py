#!/usr/bin/env python
#encoding: utf8

import os
import sys
import time
import Queue
import threading
import socket
import json
import getopt

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

def run_all(server,conf):
    print('Test from server: %s' % server)
    reports = {}

    tester = Mtu(server,conf['MTU'])
    reports['MTU'] = tester.run()

    tester = Nat(server,conf['NAT'])
    reports['NAT'] = tester.run()

    tester = DownloadSpeed(server,conf['DownloadSpeed'])
    reports['DownloadSpeed'] = tester.run()

    tester = UploadSpeed(server,conf['UploadSpeed'])
    reports['UploadSpeed'] = tester.run()

    tester = RtpDownStream(server,conf['RtpDownStream'])
    reports['RtpDownStream'] = tester.run()

    tester = UdpDelay(server,conf['UdpDelay'])
    reports['UdpDelay'] = tester.run()

    tester = TcpDelay(server,conf['TcpDelay'])
    reports['TcpDelay'] = tester.run()

    return reports

def get_file_path(cur,fpath):
    if os.path.isfile(fpath):
        return fpath
    elif os.path.isfile('%s.json' %  fpath):
        return '%s.json' % fpath
    elif os.path.isfile('%s/%s' % (cur,fpath)):
        return '%s/%s' % (cur,fpath)
    elif os.path.isfile('%s/%s.json' % (cur,fpath)):
        return '%s/%s.json' % (cur,fpath)
    else:
        return ''

def save_reports(reports):
    fname = time.strftime('%Y%m%d%H%M%S.json',time.gmtime())
    fpath = '%s/report/%s' % (current_path,fname)
    dir = os.path.dirname(fpath)

    if not os.path.exists(dir):
        os.mkdir(dir)

    content = json.dumps(reports,sort_keys=True,indent=2)
    f = open(fname,'w')
    f.write(content)
    f.close()

def main():
    shortargs = 's:f:'
    longargs = ['Server=','File=','MTU','NAT','DownloadSpeed','UploadSpeed','RtpDownStream','UdpDelay','TcpDelay']

    conf_file = '%s/conf.json' % current_path
    server = None

    opts,args = getopt.getopt(sys.argv[1:],shortargs,longargs)
    for opt,val in opts:
        if opt == '-s' or opt == '--server':
            server = val
        elif opt == '-f' or opt == '--file':
            conf_file = get_file_path(current_path,val)

    if len(conf_file) == 0:
        print('Can NOT found config file!')
        return

    conf = json.load(file(conf_file))
    if server is None:
        server = conf['server']

    print('Server: %s, File: %s' % (server,conf_file))
    reports = {}
    for opt,val in opts:
        if opt == '--MTU':
            tester = Mtu(server,conf['MTU'])
            reports['MTU'] = tester.run()
        elif opt == '--NAT':
            tester = Nat(server,conf['NAT'])
            reports['NAT'] = tester.run()
        elif opt == '--DownloadSpeed':
            tester = DownloadSpeed(server,conf['DownloadSpeed'])
            reports['DownloadSpeed'] = tester.run()
        elif opt == '--UploadSpeed':
            tester = UploadSpeed(server,conf['UploadSpeed'])
            reports['UploadSpeed'] = tester.run()
        elif opt == '--RtpDownStream':
            tester = RtpDownStream(server,conf['RtpDownStream'])
            reports['RtpDownStream'] = tester.run()
        elif opt == '--UdpDelay':
            tester = UdpDelay(server,conf['UdpDelay'])
            reports['UdpDelay'] = tester.run()
        elif opt == '--TcpDelay':
            tester = TcpDelay(server,conf['TcpDelay'])
            reports['TcpDelay'] = tester.run()

    if len(reports) == 0:
        reports = run_all()

    save_reports(reports)

if __name__ == '__main__':
    main()
