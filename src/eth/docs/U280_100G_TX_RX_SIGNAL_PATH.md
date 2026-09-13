# Tx and Rx Signal Path Analysis - Top to Ports

This document traces the Ethernet transmit (Tx) and receive (Rx) signal paths from the top-level FPGA module down to the physical GTY transceiver ports for the Alveo AU280 design.

## Design Overview
- **Board**: Alveo AU280
- **Ethernet Speed**: 100G (4x25G lanes per port)
- **Transceiver Type**: GTY (UltraScale+)
- **Ports**: 2 QSFP28 ports (QSFP0, QSFP1)
- **Data Width**: 512-bit internal datapath
- **Configuration**: Low latency mode enabled

---

## Signal Path Hierarchy

### 1. TOP LEVEL: `fpga_au280.sv` (fpga)
**Location**: `src/eth/example/Alveo/fpga/rtl/fpga_au280.sv`

#### Port Signals:
```systemverilog
// QSFP0 (Port 0)
output wire logic qsfp0_tx_p[4]    // Tx differential positive
output wire logic qsfp0_tx_n[4]    // Tx differential negative
input  wire logic qsfp0_rx_p[4]    // Rx differential positive
input  wire logic qsfp0_rx_n[4]    // Rx differential negative
input  wire logic qsfp0_mgt_refclk_0_p/n  // Reference clock

// QSFP1 (Port 1)
output wire logic qsfp1_tx_p[4]
output wire logic qsfp1_tx_n[4]
input  wire logic qsfp1_rx_p[4]
input  wire logic qsfp1_rx_n[4]
input  wire logic qsfp1_mgt_refclk_0_p/n
```

#### Internal Connections:
```systemverilog
// Array organization (8 lanes total: 2 ports × 4 lanes)
wire eth_gty_tx_p[8]     // eth_gty_tx_p[0:3] → qsfp0_tx_p
wire eth_gty_tx_n[8]     //                 [4:7] → qsfp1_tx_p
wire eth_gty_rx_p[8]     // eth_gty_rx_p[0:3] ← qsfp0_rx_p
wire eth_gty_rx_n[8]     //                 [4:7] ← qsfp1_rx_p
wire eth_gty_mgt_refclk_p[2]
wire eth_gty_mgt_refclk_n[2]
```

#### Module Instantiation:
Instantiates `fpga_core` and passes the GTY signals through.

---

### 2. CORE LEVEL: `fpga_core.sv`
**Location**: `src/eth/example/Alveo/fpga/rtl/fpga_core.sv`

#### Function:
- Contains MAC configuration (512-bit datapath)
- Manages 2 QSFP ports (GTY_QUAD_CNT = 2)
- Each port has 4 GTY channels (GTY_CNT = 8)

#### Key Signals:
```systemverilog
// From top level
input  wire logic eth_gty_tx_p[8]
input  wire logic eth_gty_tx_n[8]
output wire logic eth_gty_rx_p[8]
output wire logic eth_gty_rx_n[8]

// MAC interface (per quad/port)
wire eth_gty_tx_clk[2]              // MAC Tx clock
wire eth_gty_tx_rst[2]              // MAC Tx reset
taxi_axis_if eth_gty_axis_tx[2]     // AXI-Stream Tx data (512-bit)
wire eth_gty_rx_clk[2]              // MAC Rx clock
wire eth_gty_rx_rst[2]              // MAC Rx reset
taxi_axis_if eth_gty_axis_rx[2]     // AXI-Stream Rx data (512-bit)
```

#### Module Instantiation:
For each QSFP port (n=0,1):
```systemverilog
taxi_eth_mac_100g_us mac_inst (
    // Connects 4 GTY lanes per port
    .xcvr_txp(eth_gty_tx_p[n*4 +: 4]),
    .xcvr_txn(eth_gty_tx_n[n*4 +: 4]),
    .xcvr_rxp(eth_gty_rx_p[n*4 +: 4]),
    .xcvr_rxn(eth_gty_rx_n[n*4 +: 4]),
    // AXI-Stream interface
    .s_axis_tx(eth_gty_axis_tx[n]),
    .m_axis_rx(eth_gty_axis_rx[n])
);
```

---

### 3. MAC/PHY WRAPPER: `taxi_eth_mac_100g_us.sv`
**Location**: `src/eth/rtl/us/taxi_eth_mac_100g_us.sv`

#### Function:
- Wraps 4 GTY channels to form a 100G port
- Integrates CMAC (100G Ethernet MAC) IP core
- Provides 512-bit parallel interface

#### Signal Flow:

**TX PATH**:
```
AXI-Stream Input (512-bit) → Padding → CMAC → 4×128-bit Serdes → 4 GTY Channels
```

**RX PATH**:
```
4 GTY Channels → 4×128-bit Serdes → CMAC → AXI-Stream Output (512-bit)
```

#### Key Signals:
```systemverilog
// Serial interface (to/from channels)
output wire logic xcvr_txp[4]
output wire logic xcvr_txn[4]
input  wire logic xcvr_rxp[4]
input  wire logic xcvr_rxn[4]

// Parallel serdes interface (128-bit per lane @ 322 MHz)
wire [127:0] serdes_txdata[4]    // Tx data to GTY
wire [15:0]  serdes_txctrl0[4]   // Tx control/header
wire [15:0]  serdes_txctrl1[4]   // Tx control
wire [127:0] serdes_rxdata[4]    // Rx data from GTY
wire [15:0]  serdes_rxctrl0[4]   // Rx control/header
wire [15:0]  serdes_rxctrl1[4]   // Rx control

// Aggregated for CMAC (512-bit)
wire [511:0] cmac_txdata         // Assembled from 4×128
wire [63:0]  cmac_txctrl0        // Assembled from 4×16
wire [63:0]  cmac_txctrl1
wire [511:0] cmac_rxdata         // Split to 4×128
wire [63:0]  cmac_rxctrl0        // Split to 4×16
wire [63:0]  cmac_rxctrl1
```

#### Module Instantiation:
For each channel (n=0 to 3):
```systemverilog
taxi_eth_mac_100g_us_ch ch_inst (
    .xcvr_txp(xcvr_txp[n]),
    .xcvr_txn(xcvr_txn[n]),
    .xcvr_rxp(xcvr_rxp[n]),
    .xcvr_rxn(xcvr_rxn[n]),
    .serdes_txdata(serdes_txdata[n]),
    .serdes_txctrl0(serdes_txctrl0[n]),
    .serdes_txctrl1(serdes_txctrl1[n]),
    .serdes_rxdata(serdes_rxdata[n]),
    .serdes_rxctrl0(serdes_rxctrl0[n]),
    .serdes_rxctrl1(serdes_rxctrl1[n])
);
```

---

### 4. CHANNEL WRAPPER: `taxi_eth_mac_100g_us_ch.sv`
**Location**: `src/eth/rtl/us/taxi_eth_mac_100g_us_ch.sv`

#### Function:
- Per-channel wrapper
- Contains optional TX/RX pipeline stages for timing closure
- Connects to GTY transceiver wrapper

#### Signal Flow:

**TX PATH**:
```
serdes_txdata[127:0] → Optional Pipeline → gt_txdata[127:0] → GTY Wrapper
```

**RX PATH**:
```
GTY Wrapper → gt_rxdata[127:0] → Optional Pipeline → serdes_rxdata[127:0]
```

#### Pipeline Stages:
```systemverilog
parameter TX_SERDES_PIPELINE = 1  // 1 cycle Tx pipeline
parameter RX_SERDES_PIPELINE = 1  // 1 cycle Rx pipeline
```

#### Module Instantiation:
```systemverilog
taxi_eth_mac_100g_us_gt_ll gt_inst (  // Low latency variant
    .xcvr_txp(xcvr_txp),
    .xcvr_txn(xcvr_txn),
    .xcvr_rxp(xcvr_rxp),
    .xcvr_rxn(xcvr_rxn),
    .serdes_txdata(gt_txdata),
    .serdes_txctrl0(gt_txctrl0),
    .serdes_txctrl1(gt_txctrl1),
    .serdes_rxdata(gt_rxdata),
    .serdes_rxctrl0(gt_rxctrl0),
    .serdes_rxctrl1(gt_rxctrl1)
);
```

---

### 5. GTY WRAPPER: `taxi_eth_mac_100g_us_gt_ll.sv`
**Location**: `src/eth/rtl/us/taxi_eth_mac_100g_us_gt_ll.sv`

#### Function:
- Wraps the PHY-level GTY interface
- Provides DRP (Dynamic Reconfiguration Port) interface
- Handles GTY control and status

#### Module Instantiation:
```systemverilog
taxi_eth_phy_25g_us_gt_ll gt_inst (
    .xcvr_txp(xcvr_txp),
    .xcvr_txn(xcvr_txn),
    .xcvr_rxp(xcvr_rxp),
    .xcvr_rxn(xcvr_rxn),
    .serdes_txdata(serdes_txdata),
    .serdes_txctrl0(serdes_txctrl0),
    .serdes_txctrl1(serdes_txctrl1),
    .serdes_rxdata(serdes_rxdata),
    .serdes_rxctrl0(serdes_rxctrl0),
    .serdes_rxctrl1(serdes_rxctrl1)
);
```

---

### 6. PHY LEVEL: `taxi_eth_phy_25g_us_gt_ll.sv`
**Location**: `src/eth/rtl/us/taxi_eth_phy_25g_us_gt_ll.sv`

#### Function:
- 25G PHY layer (one per lane)
- Interfaces with GTY primitive through wizard IP
- Handles 66B/64B encoding/decoding
- Manages GTY reset sequencing

#### Signal Flow:

**TX PATH**:
```
serdes_txdata[127:0] → 66B/64B Encoding → gt_txdata[127:0] → GTY Primitive
serdes_txctrl0[15:0] → Header Generation → gt_txheader[5:0] → GTY Primitive
```

**RX PATH**:
```
GTY Primitive → gt_rxdata[127:0] → 66B/64B Decoding → serdes_rxdata[127:0]
GTY Primitive → gt_rxheader[5:0] → Header Processing → serdes_rxctrl0[15:0]
```

#### Module Instantiation:
```systemverilog
taxi_eth_phy_25g_us_gty_ll_full gt_ch_inst (  // Xilinx GTY wizard IP wrapper
    // Serial interface
    .gtytxp_out(xcvr_txp),
    .gtytxn_out(xcvr_txn),
    .gtyrxp_in(xcvr_rxp),
    .gtyrxn_in(xcvr_rxn),
    
    // Parallel interface
    .gtwiz_userdata_tx_in(gt_txdata),    // 128-bit @ 322 MHz
    .txheader_in(gt_txheader),           // 6-bit header
    .gtwiz_userdata_rx_out(gt_rxdata),   // 128-bit @ 322 MHz
    .rxheader_out(gt_rxheader),          // 6-bit header
    
    // Clocking
    .gtwiz_userclk_tx_usrclk2_out(tx_clk),  // 322.265625 MHz
    .gtwiz_userclk_rx_usrclk2_out(rx_clk),  // 322.265625 MHz
    
    // PLL
    .gtrefclk00_in(xcvr_gtrefclk00_in),  // 156.25 MHz reference
    .qpll0outclk_out(xcvr_qpll0clk_out),
    .qpll1outclk_out(xcvr_qpll1clk_out)
);
```

---

### 7. PRIMITIVE LEVEL: `taxi_eth_phy_25g_us_gty_ll_full`
**Type**: Xilinx IP (GTY Transceiver Wizard generated)

#### Function:
- Instantiates GTYE4_CHANNEL and GTYE4_COMMON primitives
- Handles:
  - Line rate: 25.78125 Gbps (25G Ethernet)
  - Reference clock: 156.25 MHz
  - User clock: 322.265625 MHz (line rate / 80)
  - Data width: 128 bits (internal width, 2 UI per bit)
  - Encoding: 66B/64B (64 data bits + 2 sync bits)

#### GTY Primitive:
```systemverilog
GTYE4_CHANNEL #(
    // Line rate configuration
    .TX_INT_DATAWIDTH(1),      // 80-bit internal
    .TX_DATA_WIDTH(128),       // 128-bit user interface
    .RX_INT_DATAWIDTH(1),
    .RX_DATA_WIDTH(128),
    
    // Protocol
    .TX_HEADER_WIDTH(6),       // 66B/64B sync header
    .RX_HEADER_WIDTH(6)
) gtye4_channel_inst (
    // Serial I/O
    .GTYTXP(gtytxp_out),
    .GTYTXN(gtytxn_out),
    .GTYRXP(gtyrxp_in),
    .GTYRXN(gtyrxn_in),
    
    // Parallel data
    .TXDATA(gtwiz_userdata_tx_in),    // 128-bit
    .TXHEADER(txheader_in),            // 6-bit
    .RXDATA(gtwiz_userdata_rx_out),    // 128-bit
    .RXHEADER(rxheader_out),           // 6-bit
    
    // User clocks
    .TXUSRCLK(gtwiz_userclk_tx_usrclk2_out),
    .RXUSRCLK(gtwiz_userclk_rx_usrclk2_out),
    
    // Reference
    .GTREFCLK0(gtrefclk00_in)
);
```

---

## Complete Signal Path Summary

### TX PATH (Top → Bottom):
```
User Application
    ↓ AXI-Stream 512-bit @ ~322 MHz
fpga_core
    ↓ AXI-Stream 512-bit
taxi_eth_mac_100g_us (×2 ports)
    ↓ AXI-Stream 512-bit → Padding → CMAC
    ↓ 512-bit SERDES (split to 4 lanes)
    ↓ 4 × 128-bit per lane
taxi_eth_mac_100g_us_ch (×4 channels per port)
    ↓ 128-bit + 16-bit ctrl (with optional pipeline)
taxi_eth_mac_100g_us_gt_ll
    ↓ 128-bit + ctrl
taxi_eth_phy_25g_us_gt_ll (25G PHY)
    ↓ 128-bit data + 6-bit header (66B/64B encoding)
taxi_eth_phy_25g_us_gty_ll_full (Xilinx IP)
    ↓ 80-bit internal @ 322 MHz
GTYE4_CHANNEL (Primitive)
    ↓ Serial 25.78125 Gbps
Physical Pins: qsfp[0|1]_tx_p[0:3], qsfp[0|1]_tx_n[0:3]
```

### RX PATH (Bottom → Top):
```
Physical Pins: qsfp[0|1]_rx_p[0:3], qsfp[0|1]_rx_n[0:3]
    ↓ Serial 25.78125 Gbps
GTYE4_CHANNEL (Primitive)
    ↓ 80-bit internal @ 322 MHz
taxi_eth_phy_25g_us_gty_ll_full (Xilinx IP)
    ↓ 128-bit data + 6-bit header
taxi_eth_phy_25g_us_gt_ll (25G PHY)
    ↓ 128-bit + ctrl (66B/64B decoding)
taxi_eth_mac_100g_us_gt_ll
    ↓ 128-bit + 16-bit ctrl
taxi_eth_mac_100g_us_ch (×4 channels per port)
    ↓ 128-bit + 16-bit ctrl (with optional pipeline)
    ↓ 4 × 128-bit per lane
taxi_eth_mac_100g_us (×2 ports)
    ↓ 512-bit SERDES (merged from 4 lanes) → CMAC
    ↓ AXI-Stream 512-bit
fpga_core
    ↓ AXI-Stream 512-bit
User Application
```

---

## Key Data Widths and Rates

| Level | TX Data Width | RX Data Width | Clock Frequency | Line Rate |
|-------|--------------|--------------|----------------|-----------|
| Application (fpga_core) | 512-bit | 512-bit | ~322 MHz | 100 Gbps |
| MAC (taxi_eth_mac_100g_us) | 512-bit | 512-bit | 322 MHz | 100 Gbps |
| Per Channel (taxi_eth_mac_100g_us_ch) | 128-bit | 128-bit | 322 MHz | 25 Gbps |
| PHY (taxi_eth_phy_25g_us_gt_ll) | 128-bit | 128-bit | 322 MHz | 25 Gbps |
| GTY Internal | 80-bit | 80-bit | 322 MHz | 25.78125 Gbps |
| GTY Serial | 1-bit | 1-bit | 25.78125 GHz | 25.78125 Gbps |

---

## Module File Locations

| Module | File Path |
|--------|-----------|
| fpga | src/eth/example/Alveo/fpga/rtl/fpga_au280.sv |
| fpga_core | src/eth/example/Alveo/fpga/rtl/fpga_core.sv |
| taxi_eth_mac_100g_us | src/eth/rtl/us/taxi_eth_mac_100g_us.sv |
| taxi_eth_mac_100g_us_ch | src/eth/rtl/us/taxi_eth_mac_100g_us_ch.sv |
| taxi_eth_mac_100g_us_gt_ll | src/eth/rtl/us/taxi_eth_mac_100g_us_gt_ll.sv |
| taxi_eth_phy_25g_us_gt_ll | src/eth/rtl/us/taxi_eth_phy_25g_us_gt_ll.sv |
| taxi_eth_phy_25g_us_gty_ll_full | Xilinx IP (generated) |

---

## Notes

1. **Low Latency Mode**: The design uses `CFG_LOW_LATENCY = 1'b1`, which selects the `_gt_ll` (low latency) variant of the GTY wrapper.

2. **Pipeline Stages**: Optional 1-cycle pipeline stages are inserted at the channel level (`TX_SERDES_PIPELINE = 1`, `RX_SERDES_PIPELINE = 1`) for timing closure.

3. **Data Rate**: Each lane operates at 25.78125 Gbps, and 4 lanes combine to provide ~100 Gbps total (after encoding overhead).

4. **Encoding**: Uses 66B/64B encoding, where 64 data bits are transmitted with 2 sync header bits, resulting in a 25/25.78125 = ~0.97 efficiency.

5. **CMAC**: The Xilinx CMACE4 100G Ethernet MAC IP core is instantiated in `taxi_eth_mac_100g_us.sv` to handle Ethernet framing, FCS, and flow control.

6. **QPLL**: QPLL0 is typically used, providing the reference for all 4 channels in a quad.

---

Document generated: 2026-09-12
