#!/usr/bin/env python
#encoding: utf8 

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import symbol_database as _symbol_database
import struct

_sym_db = _symbol_database.Default()


def pack(msg):
    if not isinstance(msg,_message.Message):
        raise TypeError('input object is not a protobuf message object!');

    name = msg.DESCRIPTOR.full_name;

    if 0 == len(name):
        raise ValueError('Message object has no type name!');

    if not msg.IsInitialized():
        raise ValueError('Message %s is not initialized!' % (name));

    data = msg.SerializeToString();
    header = struct.pack('!HH',len(name),len(data));

    packet = bytearray();
    packet.extend(header);
    packet.extend(name);

    if len(data) > 0:
        packet.extend(data);
    
    return packet;

def unpack(packet):
    if len(packet) <= 4:
        raise ValueError('Packet is too small: %d' % len(packet));

    header = packet[ : 4];
    namelen,datalen = struct.unpack('!HH',header);

    if namelen <= 0 or 4 + namelen + datalen != len(packet):
        raise ValueError('Bad packet! len=%d namelen=%d datalen=%d' % (len(packet),namelen,datalen));
    name = packet[4 : 4 + namelen];
    print('name = %s' % name);

    msg = _sym_db.GetSymbol(str(name))();

    if datalen > 0:
        data = packet[4 + namelen : ];
        print('data len= %d' % len(data));
        msg.ParseFromString(str(data));

    return (name,msg);



def unpack_from_stream(stream):
    header = stream.read(4);
    namelen,datalen = struct.unpack('!HH',header);

    if namelen <= 0:
        raise ValueError('Bad format! name len is zero');

    name = stream.read(namelen);
    msg = _sym_db.GetSymbol(str(name))();

    if datalen > 0:
        data = stream.read(datalen)
        msg.ParseFromString(str(data));

    return (name,msg);


