#!/usr/bin/python3

import socket
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
s.bind(('enp82s0', 0)) 
s.send(b'\xff'*6 + b'\x00\x11\x22\x33\x44\x55' + b'\x08\x00' + b'TEST'*15)

