# Test 10G Ethernet

On the test machine:

- Use `tcpdump` to monitor network traffic on the connected Ethernet interface, e.g., 

  ```
  sudo tcpdump -i enp82s0 -e -n -v -X
  ```

- Run script to send test packets:

  ```
  sudo ./xg-test.py
  ```

The script should print something like:

```
Sending 5 test packets...
  [0] Sent 60 bytes → Received 60 bytes ✓
  [1] Sent 60 bytes → Received 60 bytes ✓
  [2] Sent 60 bytes → Received 60 bytes ✓
  [3] Sent 60 bytes → Received 60 bytes ✓
  [4] Sent 60 bytes → Received 60 bytes ✓
```

Expect to see something from `tcpdummp` like:

```
16:05:22.849796 00:11:22:33:44:55 > ff:ff:ff:ff:ff:ff, ethertype IPv4 (0x0800), length 60: IP5 (invalid)
	0x0000:  5061 636b 6574 3058 5858 5858 5858 5858  Packet0XXXXXXXXX
	0x0010:  5858 5858 5858 5858 5858 5858 5858 5858  XXXXXXXXXXXXXXXX
	0x0020:  5858 5858 5858 5858 5858 5858 5858       XXXXXXXXXXXXXX
```

Which is the packet from the connection (loopback in PL).

