#!/usr/bin/python3

import socket
import time

INTERFACE = "enp82s0"

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
s.bind((INTERFACE, 0)) 
s.settimeout(1.0)

print("Sending 5 test packets...")
for i in range(5):
    frame = b'\xff'*6 + b'\x00\x11\x22\x33\x44\x55' + b'\x08\x00' + f'Packet{i}'.encode().ljust(46, b'X')

    s.send(frame)
    print(f"  [{i}] Sent {len(frame)} bytes", end='')

    try:
        rx, _ = s.recvfrom(2048)
        print(f" → Received {len(rx)} bytes ✓")
    except socket.timeout:
        print(" → TIMEOUT (no loopback) ✗")

    time.sleep(0.2)

s.close()


