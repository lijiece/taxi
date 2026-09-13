# ZCU106 10G Ethernet Loopback Test Plan

## Test Setup

### Hardware Requirements
- **ZCU106 FPGA board** with bitstream programmed
- **Computer** with 10G Ethernet NIC (Intel X520/X540, Mellanox ConnectX, etc.)
- **SFP+ cable/module** - Direct Attach Copper (DAC) or fiber with matching SFP+ modules
- **USB cable** for UART control interface
- **Power supply** for ZCU106

### Software Requirements
- **Linux system** (Ubuntu/RHEL/CentOS recommended)
- **ethtool** - Link status and statistics
- **iperf3** - Throughput testing
- **tcpdump/Wireshark** - Packet capture and analysis
- **Python 3** with pyserial - XFCP control interface
- **pktgen** or **MoonGen** (optional) - Advanced packet generation

### Physical Connections
```
Computer 10G NIC <---> SFP+ Port 0 (or Port 1) on ZCU106
Computer USB <---> ZCU106 USB UART (for XFCP control)
```

**Note**: The FPGA implements a **loopback** - any packet sent will be echoed back. Do NOT assign an IP address initially.

---

## Test Procedure

### Test 1: Link Establishment and Autonegotiation

**Objective**: Verify 10G link comes up with correct settings

**Steps**:
```bash
# Identify your 10G interface (e.g., eth1, enp4s0)
ip link show

# Bring interface up (no IP needed for loopback testing)
sudo ip link set <interface> up

# Check link status - should show 10000Mb/s full duplex
sudo ethtool <interface>

# Expected output:
# Speed: 10000Mb/s
# Duplex: Full
# Link detected: yes
# Auto-negotiation: on
```

**Expected Result**:
- Link LED on both NIC and ZCU106 should be lit
- Speed: 10000Mb/s
- Duplex: Full
- FEC: None (unless SFP+ module requires it)

**Troubleshooting**:
- If link down: Check SFP+ module compatibility, try different cable
- Wrong speed: Disable AN or force 10G mode: `ethtool -s <interface> speed 10000 duplex full autoneg off`

---

### Test 2: Basic Loopback Verification

**Objective**: Verify packets are looped back correctly

**Method A: Using Python (requires sudo)**:
```bash
# Terminal 1: Start packet capture
sudo tcpdump -i <interface> -e -n -v

# Terminal 2: Send a single broadcast packet
# IMPORTANT: Must run with sudo for raw socket access
sudo python3 << 'EOF'
import socket
import struct

INTERFACE = "<interface>"  # CHANGE THIS: e.g., "eth1"

# Create raw socket (requires root/sudo)
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
s.bind((INTERFACE, 0))

# Build Ethernet frame: broadcast MAC, source MAC, type, payload
frame = (
    b'\xff\xff\xff\xff\xff\xff' +  # Destination: broadcast
    b'\x00\x11\x22\x33\x44\x55' +  # Source: arbitrary MAC
    b'\x08\x00' +                   # EtherType: IPv4
    b'Hello ZCU106 Loopback!' * 3  # Payload (pad to 60 bytes min)
)

s.send(frame)
print(f"Sent {len(frame)} byte frame")
s.close()
EOF
```

**Method B: Using scapy (easier, handles permissions)**:
```bash
# Install scapy if not present
sudo apt-get install python3-scapy  # Debian/Ubuntu
# or
sudo pip3 install scapy

# Send test packet with scapy
sudo python3 << 'EOF'
from scapy.all import *

INTERFACE = "<interface>"  # CHANGE THIS

# Create a simple Ethernet frame
pkt = Ether(dst="ff:ff:ff:ff:ff:ff", src="00:11:22:33:44:55") / Raw(load="Hello ZCU106!" * 5)

# Send and capture response
print("Sending packet...")
ans, unans = srp(pkt, iface=INTERFACE, timeout=2, verbose=True)

if ans:
    print("\nLoopback SUCCESS!")
    print(f"Sent:     {ans[0][0].summary()}")
    print(f"Received: {ans[0][1].summary()}")
else:
    print("\nNo response received - check connection")
EOF
```

**Method C: Using arping (simplest, no programming)**:
```bash
# arping works even with loopback - sends ARP and listens
sudo arping -I <interface> -c 5 192.168.1.1

# Or use ping with broadcast (if IP assigned)
sudo ip addr add 192.168.100.1/24 dev <interface>
ping -I <interface> -c 5 192.168.100.255
```

**Expected Result**:
- tcpdump shows the transmitted frame
- tcpdump shows the SAME frame echoed back (loopback)
- Frame content identical (check with Wireshark for byte-by-byte comparison)
- Scapy method shows 100% response rate

---

### Test 3: Throughput Testing with iperf3

**Objective**: Measure loopback throughput at line rate

**Challenge**: iperf3 requires IP addresses, but loopback reflects packets back to sender

**Solution**: Assign IP and test with UDP (TCP won't work due to loopback behavior)

**Steps**:
```bash
# Assign IP address (arbitrary, not routable)
sudo ip addr add 192.168.100.1/24 dev <interface>

# Terminal 1: Start iperf3 UDP server
iperf3 -s -u

# Terminal 2: Run iperf3 UDP client to test throughput
# Send to broadcast or use ARP-less testing
iperf3 -c 192.168.100.255 -u -b 10G -t 30 -l 1400

# For better results, use packet generator that supports loopback
```

**Expected Result**:
- **UDP**: Up to ~9.5 Gbps (line rate accounting for Ethernet overhead)
- **Packet loss**: 0% for valid frame sizes
- **Latency**: <1 microsecond (loopback delay)

**Alternative - Raw packet generator**:
```bash
# Use pktgen (kernel module) for precise testing
sudo modprobe pktgen
echo "rem_device_all" > /proc/net/pktgen/kpktgend_0
echo "add_device <interface>" > /proc/net/pktgen/kpktgend_0
echo "count 1000000" > /proc/net/pktgen/<interface>
echo "pkt_size 1500" > /proc/net/pktgen/<interface>
echo "dst_mac ff:ff:ff:ff:ff:ff" > /proc/net/pktgen/<interface>
echo "start" > /proc/net/pktgen/pgctrl

# Check results
cat /proc/net/pktgen/<interface>
```

---

### Test 4: Frame Size Sweep

**Objective**: Test all valid Ethernet frame sizes (64 to 9216 bytes)

**Steps**:
```bash
#!/bin/bash
# frame_size_test.sh

INTERFACE="<your_interface>"

for SIZE in 64 128 256 512 1024 1500 2048 4096 8192 9216; do
    echo "Testing frame size: $SIZE bytes"
    
    # Send 10000 packets of this size
    sudo python3 << EOF
import socket
import time

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
s.bind(("$INTERFACE", 0))

frame = (
    b'\xff\xff\xff\xff\xff\xff' +
    b'\x00\x11\x22\x33\x44\x55' +
    b'\x08\x00' +
    b'X' * ($SIZE - 14)  # Subtract Ethernet header
)

start = time.time()
for i in range(10000):
    s.send(frame)
end = time.time()

print(f"Sent 10000 frames in {end-start:.3f}s")
print(f"Rate: {10000/(end-start):.1f} pps")
EOF
    
    # Check NIC statistics
    sudo ethtool -S $INTERFACE | grep -E "(tx_packets|rx_packets|errors)"
    echo "---"
done
```

**Expected Result**:
- All frame sizes: TX packets = RX packets (perfect loopback)
- No errors, no drops
- Jumbo frames (>1500 bytes) work if NIC supports them:
  ```bash
  sudo ip link set <interface> mtu 9000
  ```

---

### Test 5: Statistics Monitoring via XFCP

**Objective**: Read hardware statistics from FPGA MAC

**Steps**:
```bash
# Find USB UART device (usually /dev/ttyUSB0 or /dev/ttyUSB1)
ls -l /dev/ttyUSB*

# Create Python script to read statistics
cat > xfcp_stats.py << 'EOF'
#!/usr/bin/env python3
"""
XFCP Statistics Reader for ZCU106 10G Ethernet

Connects to FPGA via USB UART and reads MAC statistics
"""

import serial
import struct
import sys
import time

# XFCP protocol definitions (simplified)
# Full implementation in: src/xfcp/tb/xfcp.py

def cobs_encode(data):
    """Consistent Overhead Byte Stuffing encoding"""
    result = bytearray()
    code_ptr = 0
    code = 1
    
    result.append(0)  # Placeholder for first code
    
    for byte in data:
        if byte == 0:
            result[code_ptr] = code
            code_ptr = len(result)
            result.append(0)
            code = 1
        else:
            result.append(byte)
            code += 1
            if code == 0xFF:
                result[code_ptr] = code
                code_ptr = len(result)
                result.append(0)
                code = 1
    
    result[code_ptr] = code
    return bytes(result)

def cobs_decode(data):
    """Consistent Overhead Byte Stuffing decoding"""
    result = bytearray()
    i = 0
    
    while i < len(data):
        code = data[i]
        i += 1
        
        for _ in range(code - 1):
            if i >= len(data):
                return None
            result.append(data[i])
            i += 1
        
        if code < 0xFF and i < len(data):
            result.append(0)
    
    return bytes(result)

def xfcp_read_stats(port_name, baudrate=2000000):
    """Read statistics from XFCP statistics module (port 0)"""
    
    print(f"Connecting to {port_name} at {baudrate} baud...")
    ser = serial.Serial(port_name, baudrate, timeout=1)
    time.sleep(0.1)
    
    # XFCP packet: route to port 0 (stats module), read first 64 counters
    # Format: [path] [rpath] [ptype] [payload]
    # Simplified - real implementation needs proper XFCP framing
    
    print("\nXFCP Statistics Module (Port 0)")
    print("=" * 60)
    print("Note: This is a simplified demo")
    print("Full implementation requires xfcp Python library")
    print("\nTo properly read statistics:")
    print("1. Use the xfcp library from src/xfcp/tb/xfcp.py")
    print("2. Enumerate the bus to find statistics module")
    print("3. Read counter values from the statistics RAM")
    print("\nSee src/xfcp/tb/taxi_xfcp_mod_stats/ for examples")
    
    ser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 xfcp_stats.py <tty_device>")
        print("Example: python3 xfcp_stats.py /dev/ttyUSB0")
        sys.exit(1)
    
    xfcp_read_stats(sys.argv[1])
EOF

chmod +x xfcp_stats.py
python3 xfcp_stats.py /dev/ttyUSB0
```

**Expected Result**:
- Connection established to UART
- For full statistics reading, integrate with `src/xfcp/tb/xfcp.py` library
- Statistics should show:
  - TX packet count = RX packet count (loopback)
  - No FCS errors
  - No alignment errors

**Full XFCP Integration** (requires taxi library):
```bash
# Add taxi library to Python path
export PYTHONPATH=/mnt/nvme/data/fpga/u280/taxi/src/xfcp/tb:$PYTHONPATH

# Run enumeration and stats reading
# (Full script would go here - see src/xfcp/tb examples)
```

---

### Test 6: Latency Measurement

**Objective**: Measure round-trip loopback latency

**Steps**:
```bash
# Use hardware timestamping if NIC supports it
sudo ethtool -T <interface>

# If hardware timestamping available:
# Install hwstamp tool or use PTP tools

# Software method - use ping-like tool with raw sockets
cat > latency_test.py << 'EOF'
#!/usr/bin/env python3
import socket
import time
import struct
import statistics

INTERFACE = "<your_interface>"
NUM_TESTS = 1000

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
s.bind((INTERFACE, 0))

latencies = []

for i in range(NUM_TESTS):
    frame = (
        b'\xff\xff\xff\xff\xff\xff' +
        b'\x00\x11\x22\x33\x44\x55' +
        b'\x08\x00' +
        struct.pack('I', i) +
        b'X' * 42  # Pad to minimum size
    )
    
    start = time.perf_counter()
    s.send(frame)
    
    # Receive the looped back frame
    data, addr = s.recvfrom(2048)
    end = time.perf_counter()
    
    latency = (end - start) * 1_000_000  # Convert to microseconds
    latencies.append(latency)

print(f"Latency Statistics ({NUM_TESTS} samples):")
print(f"  Min:    {min(latencies):.2f} μs")
print(f"  Max:    {max(latencies):.2f} μs")
print(f"  Mean:   {statistics.mean(latencies):.2f} μs")
print(f"  Median: {statistics.median(latencies):.2f} μs")
print(f"  StdDev: {statistics.stdev(latencies):.2f} μs")
EOF

python3 latency_test.py
```

**Expected Result**:
- **Mean latency**: <2 microseconds (includes NIC + FPGA + software overhead)
- **FPGA MAC latency alone**: ~100-200 ns (low-latency mode)
- Consistent latency (low jitter)

---

### Test 7: Stress Testing

**Objective**: Long-duration stability test at line rate

**Steps**:
```bash
#!/bin/bash
# stress_test.sh

INTERFACE="<your_interface>"
DURATION=3600  # 1 hour

echo "Starting stress test for $DURATION seconds..."

# Record initial statistics
sudo ethtool -S $INTERFACE > stats_before.txt

# Generate continuous traffic using pktgen
sudo modprobe pktgen
echo "rem_device_all" > /proc/net/pktgen/kpktgend_0
echo "add_device $INTERFACE" > /proc/net/pktgen/kpktgend_0
echo "count 0" > /proc/net/pktgen/$INTERFACE  # Infinite
echo "delay 0" > /proc/net/pktgen/$INTERFACE
echo "pkt_size 1500" > /proc/net/pktgen/$INTERFACE
echo "dst_mac ff:ff:ff:ff:ff:ff" > /proc/net/pktgen/$INTERFACE

echo "start" > /proc/net/pktgen/pgctrl

# Monitor for duration
for i in $(seq 1 $((DURATION / 60))); do
    sleep 60
    echo "[$i min] Checking statistics..."
    sudo ethtool -S $INTERFACE | grep -E "(packets|errors|dropped)"
done

# Stop traffic
echo "stop" > /proc/net/pktgen/pgctrl

# Record final statistics
sudo ethtool -S $INTERFACE > stats_after.txt

# Compare
echo "Statistics comparison:"
diff stats_before.txt stats_after.txt
```

**Expected Result**:
- **Zero packet loss** over entire test period
- **TX packets ≈ RX packets**
- **No errors**: CRC, alignment, overflow
- **Stable throughput**: ~9.5 Gbps sustained

---

## Troubleshooting Guide

### Issue: "Operation not permitted" or "Permission denied"
**Cause**: Raw sockets require root privileges

**Solutions**:
```bash
# Option 1: Always use sudo for network testing scripts
sudo python3 test_script.py

# Option 2: Run Python as root
sudo -i
python3 test_script.py

# Option 3: Use scapy which handles permissions better
sudo apt-get install python3-scapy
sudo python3 -c "from scapy.all import *; sendp(Ether()/Raw('test'), iface='eth1')"

# Option 4: Grant CAP_NET_RAW capability (persistent, use carefully)
# NOT RECOMMENDED for security reasons
# sudo setcap cap_net_raw+ep $(which python3)
```

### Issue: Link doesn't come up
**Possible causes**:
- SFP+ module compatibility
- Wrong reference clock (should be 156.25 MHz)
- GT transceiver issues

**Debug**:
```bash
# Check dmesg for NIC errors
dmesg | tail -50

# Try forcing link settings
sudo ethtool -s <interface> autoneg off speed 10000 duplex full

# Check XFCP GTH control (port 1) for transceiver status
```

### Issue: Packets transmitted but none received
**Possible causes**:
- Loopback FIFO issue
- Clock domain crossing problem
- FPGA not programmed correctly

**Debug**:
```bash
# Verify bitstream is loaded
# Check LED patterns on ZCU106

# Capture with Wireshark to see if frames are malformed
sudo wireshark -i <interface> -k
```

### Issue: High packet loss
**Possible causes**:
- NIC buffer overflow
- Driver issues
- Cable quality

**Debug**:
```bash
# Increase RX ring buffer
sudo ethtool -G <interface> rx 4096 tx 4096

# Check for hardware errors
sudo ethtool -S <interface> | grep err
```

### Issue: Low throughput
**Possible causes**:
- Flow control enabled
- NIC offloading disabled
- System CPU bottleneck

**Debug**:
```bash
# Disable flow control
sudo ethtool -A <interface> rx off tx off

# Enable offloading
sudo ethtool -K <interface> gso on tso on gro on

# Check CPU usage
top -d 1
```

---

## Automated Test Script

**Complete test automation**:
```bash
#!/bin/bash
# automated_test.sh - Complete ZCU106 10G loopback test suite

INTERFACE="eth1"  # CHANGE THIS
TEST_RESULTS="test_results_$(date +%Y%m%d_%H%M%S).log"

echo "ZCU106 10G Ethernet Loopback Test Suite" | tee $TEST_RESULTS
echo "=========================================" | tee -a $TEST_RESULTS
echo "Interface: $INTERFACE" | tee -a $TEST_RESULTS
echo "Start time: $(date)" | tee -a $TEST_RESULTS
echo "" | tee -a $TEST_RESULTS

# Test 1: Link status
echo "[TEST 1] Link Establishment" | tee -a $TEST_RESULTS
sudo ip link set $INTERFACE up
sleep 2
sudo ethtool $INTERFACE | grep -E "(Speed|Duplex|Link)" | tee -a $TEST_RESULTS
echo "" | tee -a $TEST_RESULTS

# Test 2: Frame size sweep
echo "[TEST 2] Frame Size Sweep" | tee -a $TEST_RESULTS
for SIZE in 64 128 512 1500 9000; do
    echo "  Testing $SIZE byte frames..." | tee -a $TEST_RESULTS
    # Add actual test here
done
echo "" | tee -a $TEST_RESULTS

# Test 3: Statistics check
echo "[TEST 3] Statistics" | tee -a $TEST_RESULTS
sudo ethtool -S $INTERFACE | tee -a $TEST_RESULTS
echo "" | tee -a $TEST_RESULTS

echo "Tests complete: $(date)" | tee -a $TEST_RESULTS
echo "Results saved to: $TEST_RESULTS"
```

---

## Success Criteria

✅ **PASS** if ALL conditions met:
- Link establishes at 10000 Mb/s full duplex
- TX packet count = RX packet count (±1% for timing)
- Zero CRC/FCS errors
- Zero alignment errors  
- Throughput >9 Gbps for 1500-byte frames
- Latency <2 μs round-trip
- 1-hour stress test with 0% packet loss

⚠️ **PARTIAL** if:
- Link up but occasional packet loss (<0.01%)
- Throughput 8-9 Gbps (acceptable)
- Some frame sizes fail (check MTU settings)

❌ **FAIL** if:
- No link establishment
- >1% packet loss
- Consistent CRC errors
- Throughput <8 Gbps

---

## Additional Resources

- **XFCP Python Library**: `src/xfcp/tb/xfcp.py`
- **Simulation Tests**: `src/eth/example/ZCU106/fpga/tb/fpga_core/`
- **MAC Documentation**: Check `src/eth/rtl/` for taxi_eth_mac_25g_us module
- **Community**: https://corundum.zulipchat.com/
