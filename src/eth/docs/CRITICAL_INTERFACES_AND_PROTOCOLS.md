# Critical Interfaces and Protocols in Ethernet Design

This document describes the key interfaces and protocols used in the Taxi Ethernet design, their roles, data formats, and how they connect different layers of the architecture.

---

## Interface Hierarchy Overview

```
Application Layer
    ↕ AXI-Stream (AXIS)
MAC Layer
    ↕ XGMII / CGMII
PCS Layer (BASE-R Encoding)
    ↕ Serdes Interface (64B/66B)
PHY Layer
    ↕ GTY/GTH Transceiver Interface
Physical Layer (Serial)

Control Path: APB / XFCP
Autonegotiation: USXGMII
```

---

## 1. AXI-Stream (AXIS)

### 1.1 Description

**AXI-Stream** is the primary interface for packet data transfer between the application and the MAC layer. It's based on the ARM AMBA AXI4-Stream protocol.

### 1.2 Role

- **Application ↔ MAC**: Primary data path interface
- Provides flow control and packet delimitation
- Supports variable-length packets with byte-level granularity

### 1.3 Key Signals

```systemverilog
// Basic AXI-Stream signals
logic [DATA_W-1:0]  tdata   // Data bus (32, 64, 128, 512-bit)
logic [KEEP_W-1:0]  tkeep   // Byte valid indicators
logic               tvalid  // Data valid
logic               tready  // Ready to accept (backpressure)
logic               tlast   // End of packet

// Extended signals (Taxi-specific)
logic [ID_W-1:0]    tid     // Transaction ID / port ID
logic [DEST_W-1:0]  tdest   // Destination
logic [USER_W-1:0]  tuser   // User-defined (e.g., error flags, timestamps)
```

### 1.4 Data Width Variants

| Configuration | TX Data Width | RX Data Width | Clock Frequency |
|---------------|---------------|---------------|-----------------|
| 10G (per lane) | 32-bit | 32-bit | 156.25 MHz |
| 25G (per lane) | 64-bit | 64-bit | 322 MHz |
| 100G (bonded) | 512-bit | 512-bit | 322 MHz |

### 1.5 Packet Format

```
┌─────────────────────────────────────────────────────┐
│ Preamble (added by MAC) │ Dest MAC │ Src MAC │ ... │
└─────────────────────────────────────────────────────┘
         ↑
    AXI-Stream presents Ethernet frame without preamble/SFD
    
Cycle 0: tvalid=1, tdata=DA[47:0]||SA[15:0], tkeep=0xFF, tlast=0
Cycle 1: tvalid=1, tdata=SA[47:16]||EtherType||..., tkeep=0xFF, tlast=0
...
Cycle N: tvalid=1, tdata=...||FCS, tkeep=0x0F, tlast=1
```

### 1.6 Flow Control

- **Backpressure**: Receiver asserts `tready=0` to pause sender
- **Credits**: Optional completion interface (`m_axis_tx_cpl`) for transmit buffering
- **Bubble cycles**: `tvalid=0` creates idle cycles in the stream

### 1.7 Taxi Implementation

```systemverilog
// Taxi uses SystemVerilog interfaces for cleaner connections
taxi_axis_if #(
    .DATA_W(32),        // Data width
    .KEEP_W(4),         // Keep width (DATA_W/8)
    .KEEP_EN(1),        // Enable keep signal
    .LAST_EN(1),        // Enable last signal
    .ID_EN(1),          // Enable ID field
    .ID_W(8),           // ID width
    .DEST_EN(0),        // Enable dest field
    .USER_EN(1),        // Enable user field
    .USER_W(1)          // User width
) axis_interface ();
```

### 1.8 Usage in Design

- **fpga_core**: Connects application logic to MAC instances
- **MAC layer**: Primary packet ingress/egress interface
- **Statistics**: Side-band interface for counter updates (`axis_stat`)

---

## 2. XGMII (10 Gigabit Media Independent Interface)

### 2.1 Description

**XGMII** is the standard interface between the MAC and PCS layers for 10G Ethernet, defined in IEEE 802.3 Clause 46.

### 2.2 Role

- **MAC ↔ PCS**: Standardized boundary for 10G designs
- Provides byte-parallel data with control/data indicators
- Clock synchronous (156.25 MHz for 32-bit, 312.5 MHz for 64-bit)

### 2.3 Key Signals

#### 2.3.1 32-bit XGMII (10G)

```systemverilog
// TX Interface
logic [31:0]  xgmii_txd     // Transmit data (4 bytes)
logic [3:0]   xgmii_txc     // Transmit control (1 bit per byte)

// RX Interface  
logic [31:0]  xgmii_rxd     // Receive data (4 bytes)
logic [3:0]   xgmii_rxc     // Receive control (1 bit per byte)
```

#### 2.3.2 64-bit XGMII (10G DDR or 25G)

```systemverilog
logic [63:0]  xgmii_txd     // Transmit data (8 bytes)
logic [7:0]   xgmii_txc     // Transmit control (1 bit per byte)
```

### 2.4 Control vs Data Encoding

| txc | txd[7:0] | Meaning |
|-----|----------|---------|
| 0   | 0xXX     | Data byte |
| 1   | 0x07     | Idle (no packet) |
| 1   | 0xFB     | Start of packet |
| 1   | 0xFD     | Terminate (end of packet) |
| 1   | 0xFE     | Error |
| 1   | 0x9C     | Sequence ordered set |

### 2.5 Example: XGMII Packet Transmission

```
Cycle | txc  | txd[31:0]           | Description
------|------|---------------------|-------------
  0   | 0x0  | 0x55_55_55_55       | Preamble
  1   | 0x0  | 0xD5_55_55_55       | Preamble + SFD
  2   | 0x0  | 0xDA_DA_DA_DA       | Destination MAC bytes 0-3
  3   | 0x0  | 0xSA_SA_DA_DA       | Dest[4-5] + Source[0-1]
  ...
  N   | 0xF  | 0x07_07_07_FD       | End + 3 Idles
```

### 2.6 XGMII → BASE-R Conversion

XGMII is converted to BASE-R encoding for transmission over serdes:

- **Taxi module**: `taxi_xgmii_baser_enc` / `taxi_xgmii_baser_dec`
- **Encodes** XGMII control codes into 64B/66B format
- **Handles** block boundaries and scrambling

---

## 3. BASE-R Encoding (64B/66B)

### 3.1 Description

**BASE-R** is the Physical Coding Sublayer (PCS) encoding used for 10GBASE-R and higher rates, defined in IEEE 802.3 Clause 49.

### 3.2 Role

- **PCS Layer**: Encodes XGMII data for serial transmission
- Provides DC balance and sufficient transitions for clock recovery
- Adds sync headers for block alignment

### 3.3 Encoding Format

#### 3.3.1 66-bit Block Structure

```
┌──────┬─────────────────────────────────────────┐
│ Sync │         64-bit Payload                  │
│  2b  │        (Data or Control)                │
└──────┴─────────────────────────────────────────┘

Sync Header:
  01 = Data block (8 bytes of data)
  10 = Control block (contains control codes)
```

#### 3.3.2 Data Block (01 header)

```
Sync: 01
Payload: [D7][D6][D5][D4][D3][D2][D1][D0]
  All 8 bytes are data (from XGMII with txc=0)
```

#### 3.3.3 Control Block (10 header)

```
Sync: 10
Payload: [Block Type Code][Control/Data mix]

Example control block types:
  0x1E = Idle block (/I/)
  0x78 = Start block (/S/ + data)
  0x87 = Terminate block (data + /T/)
```

### 3.4 64B/66B vs 66B/64B Terminology

- **10G**: Called "64B/66B" - 64 bits encoded into 66 bits
- **25G/100G**: Often called "66B/64B" - emphasizes decoding direction
- Same encoding scheme, different naming conventions

### 3.5 Scrambling

- **Polynomial**: x^58 + x^39 + 1
- **Purpose**: Ensure DC balance, eliminate long runs
- **Self-synchronizing**: Scrambler state derived from data

### 3.6 Taxi Modules

```systemverilog
// 32-bit XGMII to 64-bit BASE-R
taxi_axis_baser_tx_32 tx_encoder (
    .clk(clk_156mhz),
    .xgmii_txd(xgmii_txd),      // 32-bit XGMII
    .xgmii_txc(xgmii_txc),      // 4-bit control
    .encoded_tx_data(serdes_tx), // 64-bit output
    .encoded_tx_hdr(serdes_hdr)  // 2-bit sync header
);

// 64-bit BASE-R to 32-bit XGMII
taxi_axis_baser_rx_32 rx_decoder (
    .clk(clk_156mhz),
    .encoded_rx_data(serdes_rx), // 64-bit input
    .encoded_rx_hdr(serdes_hdr),  // 2-bit sync header
    .xgmii_rxd(xgmii_rxd),       // 32-bit XGMII
    .xgmii_rxc(xgmii_rxc)        // 4-bit control
);
```

---

## 4. Serdes Interface

### 4.1 Description

**Serdes** (Serializer/Deserializer) is the parallel interface between the PCS and the transceiver hard IP.

### 4.2 Role

- **PCS ↔ Transceiver**: High-speed parallel data path
- Converts between parallel (64-bit) and transceiver's internal width
- Operating at user clock rate (156.25 MHz or 322 MHz)

### 4.3 Key Signals (10G)

```systemverilog
// TX Serdes (PCS → Transceiver)
logic [63:0]  serdes_txdata    // 64-bit parallel data
logic [1:0]   serdes_txheader  // 2-bit sync header (01 or 10)

// RX Serdes (Transceiver → PCS)
logic [63:0]  serdes_rxdata    // 64-bit parallel data
logic [1:0]   serdes_rxheader  // 2-bit sync header
logic         serdes_rx_bitslip // Bit alignment request
```

### 4.4 Key Signals (25G)

```systemverilog
// TX Serdes (PCS → Transceiver)
logic [127:0] serdes_txdata    // 128-bit parallel data
logic [15:0]  serdes_txctrl0   // Control bits
logic [15:0]  serdes_txctrl1   // Additional control

// RX Serdes (Transceiver → PCS)
logic [127:0] serdes_rxdata    // 128-bit parallel data
logic [15:0]  serdes_rxctrl0   // Control bits
logic [15:0]  serdes_rxctrl1   // Additional control
```

### 4.5 Clock Domains

- **10G**: Single clock domain at 156.25 MHz
- **25G**: Single clock domain at 322.265625 MHz
- **100G**: Synchronous across 4 lanes at 322.265625 MHz

### 4.6 Data Flow

#### 4.6.1 10G Serdes (64-bit @ 156.25 MHz)

```
156.25 MHz clock cycle:
┌────────────────────────────────────┐
│ [1:0] Header │ [63:0] Data          │ → 66 bits per cycle
└────────────────────────────────────┘
     ↓
Transceiver serializes to 10.3125 Gbps
(66 bits × 156.25 MHz = 10.3125 Gbps)
```

#### 4.6.2 25G Serdes (128-bit @ 322 MHz)

```
322 MHz clock cycle:
┌────────────────────────────────────┐
│ 128-bit Data + Control             │ → Internal encoding
└────────────────────────────────────┘
     ↓
Transceiver serializes to 25.78125 Gbps
```

### 4.7 Pipeline Stages

Optional pipeline registers for timing closure:
```systemverilog
parameter TX_SERDES_PIPELINE = 1  // Add 1 cycle latency
parameter RX_SERDES_PIPELINE = 1  // Add 1 cycle latency

// Implemented in taxi_eth_mac_*_us_ch modules
```

---

## 5. APB (Advanced Peripheral Bus)

### 5.1 Description

**APB** is a low-bandwidth control interface from the ARM AMBA specification, used for accessing transceiver control registers.

### 5.2 Role

- **Control Path**: Configure transceivers, read status
- **DRP Access**: Dynamic Reconfiguration Port of GTY/GTH
- **Register Interface**: APB is converted to DRP internally

### 5.3 Key Signals

```systemverilog
// APB Interface
logic [ADDR_W-1:0]  paddr     // Address (typically 16-18 bits)
logic               psel      // Select
logic               penable   // Enable (2nd cycle)
logic               pwrite    // Write enable (1=write, 0=read)
logic [DATA_W-1:0]  pwdata    // Write data (typically 16-bit)
logic [DATA_W-1:0]  prdata    // Read data
logic               pready    // Ready (can extend transfer)
logic               pslverr   // Error response
```

### 5.4 APB Transaction Timing

```
         ┌───┬───┬───┬───
psel     │ 0 │ 1 │ 1 │ 0
         ┼───┼───┼───┼───
penable  │ 0 │ 0 │ 1 │ 0
         ┼───┼───┼───┼───
paddr    │ X │ A │ A │ X
         ┼───┼───┼───┼───
pwrite   │ X │ W │ W │ X
         ┼───┼───┼───┼───
pwdata   │ X │ D │ D │ X
         ┼───┼───┼───┼───
prdata   │ X │ X │ D │ X
         ┼───┼───┼───┼───
pready   │ X │ 0 │ 1 │ X
         └───┴───┴───┴───
         IDLE SETUP ACCESS IDLE
```

### 5.5 Hierarchy in Design

```
XFCP (via UART)
    ↓
taxi_xfcp_mod_apb
    ↓ APB Master
taxi_apb_interconnect_1s (address decoder)
    ↓ APB Slaves (per GT channel)
taxi_eth_phy_*_gt_apb (APB → DRP converter)
    ↓ DRP Interface
GTY/GTH Transceiver Primitives
```

### 5.6 Typical Register Access

```systemverilog
// Read GT RX CDR lock status
apb_read(ADDR_GT_STATUS, data);
rx_cdr_lock = data[15];

// Configure GT TX pre-emphasis
apb_write(ADDR_TX_DIFFCTRL, 5'd16);  // TX drive strength
apb_write(ADDR_TX_POSTCURSOR, 5'd5); // Post-cursor
apb_write(ADDR_TX_PRECURSOR, 5'd3);  // Pre-cursor
```

---

## 6. XFCP (Extensible FPGA Control Platform)

### 6.1 Description

**XFCP** is a lightweight control protocol used in Taxi designs for configuration and monitoring over UART or Ethernet.

### 6.2 Role

- **System Control**: Access internal registers and statistics
- **Remote Debug**: Runtime configuration without JTAG
- **Statistics Collection**: Read MAC/PHY counters

### 6.3 Protocol Stack

```
XFCP Application Layer
    ↓
XFCP Switch/Router (addressing)
    ↓
XFCP Transport (framing)
    ↓
COBS Encoding (byte stuffing)
    ↓
UART Physical Layer (115200 - 3 Mbps)
```

### 6.4 Packet Format

```
┌──────────────────────────────────────────────┐
│ COBS Framing │ XFCP Header │ Payload │ CRC  │
└──────────────────────────────────────────────┘

XFCP Header:
  - Destination port
  - Source port  
  - Sequence number
  - Command/Response type
```

### 6.5 XFCP Modules in Design

```systemverilog
// UART Interface
taxi_xfcp_if_uart uart_if (
    .uart_rxd(uart_rxd),
    .uart_txd(uart_txd),
    .xfcp_dsp_ds(xfcp_downstream),
    .xfcp_dsp_us(xfcp_upstream)
);

// Switch for multiple endpoints
taxi_xfcp_switch #(
    .XFCP_ID_STR("ZCU106"),
    .PORTS(2)
) xfcp_switch (
    .xfcp_usp_ds(xfcp_upstream),
    .xfcp_dsp_ds(xfcp_downstream_ports)
);

// APB Master endpoint
taxi_xfcp_mod_apb apb_master (
    .xfcp_usp_ds(xfcp_downstream_ports[0]),
    .m_apb(apb_to_transceivers)
);

// Statistics endpoint
taxi_xfcp_mod_stats stats (
    .xfcp_usp_ds(xfcp_downstream_ports[1]),
    .s_axis_stat(statistics_stream)
);
```

### 6.6 Use Cases

1. **Initial Configuration**: Set MAC addresses, enable ports
2. **Runtime Tuning**: Adjust transceiver equalization
3. **Statistics**: Read packet counters, error rates
4. **Diagnostics**: Read internal state machines

---

## 7. USXGMII (Universal Serial 10G MII)

### 7.1 Description

**USXGMII** is a reduced-pin-count variant of XGMII that uses a single high-speed serial lane with in-band autonegotiation, defined in IEEE 802.3 Clause 116.

### 7.2 Role

- **Autonegotiation**: Automatic speed/duplex negotiation
- **Multi-Rate**: Supports 10M/100M/1G/2.5G/5G/10G on same interface
- **SFP+ Compatibility**: Standard for SFP+ modules

### 7.3 Supported Speeds

| Speed | Line Rate | Encoding |
|-------|-----------|----------|
| 10M   | 10 Mbps   | 8B/10B + Rate adaptation |
| 100M  | 100 Mbps  | 8B/10B + Rate adaptation |
| 1G    | 1.25 Gbps | 8B/10B |
| 2.5G  | 3.125 Gbps | 64B/66B + Gearbox |
| 5G    | 5.15625 Gbps | 64B/66B + Gearbox |
| 10G   | 10.3125 Gbps | 64B/66B |

### 7.4 Autonegotiation Process

```
1. Both sides send `/C1/` and `/C2/` ordered sets
2. Base page exchange (capabilities)
3. Speed and duplex resolution
4. Link training (if required)
5. Data transmission begins
```

### 7.5 USXGMII Control Codes
```
`/C1/` = Configuration ordered set 1
`/C2/` = Configuration ordered set 2
`/I/`  = Idle
`/D/`  = Data
```

### 7.6 Advertisement Format (16-bit)

```
Bit  15: Link status
Bit  14: Clock stability
Bits 13-12: Duplex mode
Bits 11-9: Speed (000=10M, 001=100M, 010=1G, ...)
Bits 8-0: Reserved/Vendor specific
```

### 7.7 Taxi Implementation

```systemverilog
taxi_eth_phy_10g_usxgmii_an autoneg (
    .clk(clk_156mhz),
    .rst(rst),
    
    // Control
    .an_en(1'b1),                     // Enable autoneg
    .an_restart(1'b0),                // Restart request
    .an_speedup(1'b0),                // Fast autoneg (sim)
    
    // Advertisement
    .an_adv_ability_usxgmii(16'h1601), // 10G, full duplex
    
    // Status
    .an_complete(an_done),
    .an_running(an_active),
    .an_usxgmii_mode(usxgmii_active),
    
    // Link partner
    .an_lp_adv_ability(lp_ability),
    .an_lp_usxgmii_speed(lp_speed),   // Resolved speed
    
    // Serdes interface
    .serdes_tx_data(tx_data),
    .serdes_rx_data(rx_data)
);
```

---

## 8. Additional Protocols

### 8.1 RS-FEC (Reed-Solomon Forward Error Correction)

- **Used in**: 100G configuration (25G lanes)
- **Standard**: IEEE 802.3 Clause 91
- **Location**: Between PCS and PMA in CMAC
- **Benefit**: Improves BER from 10^-5 to 10^-15

### 8.2 Flow Control Protocols

#### 8.2.1 802.3 PAUSE (Link-Level Flow Control)

```systemverilog
// Transmit PAUSE frame
.tx_lfc_req(1'b1),           // Request pause
.tx_lfc_quanta(16'hFFFF),    // Pause time (512-bit times)

// Receive PAUSE frame
.rx_lfc_en(1'b1),            // Enable pause reception
.rx_lfc_req(rx_pause_active), // Pause is active
```

#### 8.2.2 802.3 PFC (Priority Flow Control)

```systemverilog
// Per-priority (0-7) flow control
.tx_pfc_req(8'b0000_0011),   // Request pause on priority 0,1
.tx_pfc_quanta[0](16'hFFFF), // Pause time for priority 0
.rx_pfc_en(8'b1111_1111),    // Enable all priorities
```

### 8.2.3 PTP (Precision Time Protocol)

```systemverilog
// Timestamp interface (when PTP_TS_EN=1)
.ptp_clk(ptp_clock),              // PTP reference
.tx_ptp_ts_in(current_timestamp),  // Current time
.tx_ptp_ts_out(tx_timestamp),      // TX packet timestamp
.rx_ptp_ts_out(rx_timestamp)       // RX packet timestamp
```

---

## 9. Interface Connection Summary

### 9.1 10G Configuration Data Flow

```
Application
    ↓ AXI-Stream (32-bit @ 156 MHz)
MAC (taxi_eth_mac_10g)
    ↓ XGMII (32-bit @ 156 MHz)
PCS Encoder (taxi_axis_baser_tx_32)
    ↓ BASE-R (64-bit @ 156 MHz with 2-bit header)
PHY (taxi_eth_phy_10g)
    ↓ Serdes (64-bit @ 156 MHz)
Transceiver (GTY/GTH)
    ↓ Serial (10.3125 Gbps)
```

### 9.2 100G Configuration Data Flow

```
Application
    ↓ AXI-Stream (512-bit @ 322 MHz)
CMAC (Xilinx IP)
    ↓ Internal CGMII (512-bit)
    ↓ BASE-R + RS-FEC per lane
    ↓ Serdes (4×128-bit @ 322 MHz)
Transceiver (GTY × 4)
    ↓ Serial (4 × 25.78125 Gbps)
```

### 9.3 Control Path

```
UART/Ethernet
    ↓ XFCP
Switch/Router
    ├→ Statistics Module → AXI-Stream stats
    ├→ APB Master → APB → DRP → Transceivers
    └→ Register Interface → Configuration
```

---

## 10. Performance Considerations

### 10.1 Latency Sources

| Interface | Typical Latency | Notes |
|-----------|----------------|-------|
| AXI-Stream | ~2 cycles | Includes CDC if needed |
| MAC Processing | 4-8 cycles | FCS, padding, statistics |
| BASE-R Encoding | 2-3 cycles | Block formation |
| Serdes Pipeline | 1-2 cycles | Optional registers |
| Transceiver | 3-5 cycles | Internal pipelining |
| **Total (10G)** | **12-20 cycles** | ~77-128 ns @ 156 MHz |
| **Total (100G)** | **20-30 cycles** | ~62-93 ns @ 322 MHz |

### 10.2 Throughput

- **AXI-Stream**: Line rate with proper ready/valid handling
- **XGMII**: No back-pressure, must absorb at line rate
- **BASE-R**: Continuous, no flow control at this layer

### 10.3 Clock Domain Crossings

| Interface | CDC Required? | Method |
|-----------|--------------|---------|
| AXI-Stream | Sometimes | Async FIFO if different domains |
| XGMII | No | Synchronous to MAC clock |
| BASE-R | No | Synchronous to user clock |
| Serdes | No | Synchronous to recovered clock |
| APB | Yes | Dual-clock FIFO or gray-code |

---

## 11. Best Practices

### 11.1 AXI-Stream Design

1. **Never drop tvalid**: Once asserted, keep until tready
2. **Handle backpressure**: Always check tready before progressing
3. **Align tlast**: Must coincide with last valid byte
4. **Use tkeep properly**: Set to 0 for invalid byte lanes

### 11.2 XGMII Handling

1. **No backpressure**: Must be ready to receive every cycle
2. **Idle injection**: Insert /I/ when no data available
3. **Error propagation**: Use /E/ to signal errors mid-packet

### 11.3 Control Interface

1. **APB timeout**: Implement timeout for hung transactions
2. **XFCP framing**: Ensure COBS encoding correctness
3. **Read-modify-write**: Use for register bit-fields

---

