# U280 10G Ethernet - Tx and Rx Signal Path Analysis

This document traces the Ethernet transmit (Tx) and receive (Rx) signal paths from the top-level FPGA module down to the physical GTY transceiver ports for the **Alveo AU280 10G Ethernet configuration**.

## Design Overview
- **Board**: Alveo AU280
- **Ethernet Speed**: 10G per lane
- **Transceiver Type**: GTY (UltraScale+)
- **Ports**: 2 QSFP28 ports (QSFP0, QSFP1) - can support 4 lanes each
- **Data Width**: 32-bit internal datapath per lane
- **Configuration**: Low latency mode enabled, combined MAC+PCS
- **Encoding**: 64B/66B (BASE-R)

---

## Signal Path Hierarchy

### 1. TOP LEVEL: `fpga_au280.sv` (fpga)
**Location**: `src/eth/example/Alveo/fpga/rtl/fpga_au280.sv`

#### Configuration:
```systemverilog
parameter MAC_DATA_W = 32  // 10G configuration (32-bit datapath)
```

#### Port Signals:
```systemverilog
// QSFP0 (Port 0)
output wire logic qsfp0_tx_p[4]    // Tx differential positive
output wire logic qsfp0_tx_n[4]    // Tx differential negative
input  wire logic qsfp0_rx_p[4]    // Rx differential positive
input  wire logic qsfp0_rx_n[4]    // Rx differential negative
input  wire logic qsfp0_mgt_refclk_0_p/n  // 156.25 MHz reference clock

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
```

---

### 2. CORE LEVEL: `fpga_core.sv`
**Location**: `src/eth/example/Alveo/fpga/rtl/fpga_core.sv`

#### Configuration:
```systemverilog
parameter MAC_DATA_W = 32  // 32-bit per lane for 10G

localparam MAC_CNT = MAC_DATA_W > 64 ? GTY_QUAD_CNT : GTY_CNT;
// When MAC_DATA_W = 32: MAC_CNT = GTY_CNT = 8 (one MAC per lane)
```

#### Key Signals:
```systemverilog
// From top level (8 lanes total)
input  wire logic eth_gty_tx_p[8]
input  wire logic eth_gty_tx_n[8]
output wire logic eth_gty_rx_p[8]
output wire logic eth_gty_rx_n[8]

// MAC interface (per lane for 10G)
wire eth_gty_tx_clk[8]              // MAC Tx clock per lane
wire eth_gty_tx_rst[8]              // MAC Tx reset per lane
taxi_axis_if eth_gty_axis_tx[8]     // AXI-Stream Tx data (32-bit per lane)
taxi_axis_if eth_gty_axis_tx_cpl[8] // AXI-Stream Tx completion
wire eth_gty_rx_clk[8]              // MAC Rx clock per lane
wire eth_gty_rx_rst[8]              // MAC Rx reset per lane
taxi_axis_if eth_gty_axis_rx[8]     // AXI-Stream Rx data (32-bit per lane)
```

#### Module Instantiation:
For each QSFP port (n=0,1), since MAC_DATA_W != 512:
```systemverilog
taxi_eth_mac_25g_us mac_inst (
    .CNT(4),                        // 4 lanes per port
    .DATA_W(32),                    // 32-bit datapath (10G)
    .USXGMII_EN(1),                 // Enable USXGMII autonegotiation
    .GT_TYPE("GTY"),
    .COMBINED_MAC_PCS(1),
    
    // Serial interface (4 lanes per port)
    .xcvr_txp(eth_gty_tx_p[n*4 +: 4]),
    .xcvr_txn(eth_gty_tx_n[n*4 +: 4]),
    .xcvr_rxp(eth_gty_rx_p[n*4 +: 4]),
    .xcvr_rxn(eth_gty_rx_n[n*4 +: 4]),
    
    // Parallel interface (array of 4)
    .s_axis_tx(eth_gty_axis_tx[n*4 +: 4]),
    .m_axis_rx(eth_gty_axis_rx[n*4 +: 4]),
    .rx_clk(eth_gty_rx_clk[n*4 +: 4]),
    .tx_clk(eth_gty_tx_clk[n*4 +: 4])
);
```

---

### 3. MAC/PHY WRAPPER: `taxi_eth_mac_25g_us.sv`
**Location**: `src/eth/rtl/us/taxi_eth_mac_25g_us.sv`

#### Function:
- Wraps CNT (typically 4) GTY channels
- Each channel operates independently at 10G
- Supports 10G/25G with different DATA_W settings
- Provides per-lane 32-bit or 64-bit parallel interface

#### Key Parameters:
```systemverilog
parameter CNT = 4                    // 4 channels per quad
parameter DATA_W = 32                // 32-bit for 10G
parameter COMBINED_MAC_PCS = 1       // Integrated MAC+PCS
parameter USXGMII_EN = 1             // Enable USXGMII autonegotiation
parameter TX_SERDES_PIPELINE = 1     // 1-cycle Tx pipeline
parameter RX_SERDES_PIPELINE = 1     // 1-cycle Rx pipeline
```

#### Signal Flow:

**TX PATH** (per channel):
```
AXI-Stream Input (32-bit) → MAC → PCS → PHY → 64-bit Serdes → GTY Channel
```

**RX PATH** (per channel):
```
GTY Channel → 64-bit Serdes → PHY → PCS → MAC → AXI-Stream Output (32-bit)
```

#### Key Signals:
```systemverilog
// Serial interface (per channel)
output wire logic xcvr_txp[CNT]      // CNT = 4
output wire logic xcvr_txn[CNT]
input  wire logic xcvr_rxp[CNT]
input  wire logic xcvr_rxn[CNT]

// Parallel interface (per channel)
output wire logic rx_clk[CNT]        // Per-channel rx clock
output wire logic tx_clk[CNT]        // Per-channel tx clock
taxi_axis_if.snk s_axis_tx[CNT]      // 32-bit AXI-Stream Tx per channel
taxi_axis_if.src m_axis_rx[CNT]      // 32-bit AXI-Stream Rx per channel
```

#### Module Instantiation:
For each channel (n=0 to CNT-1):
```systemverilog
// MAC/PHY instance (per channel)
taxi_eth_mac_phy_10g mac_phy_inst (
    .DATA_W(DATA_W),                 // 32-bit for 10G
    .COMBINED_MAC_PCS(COMBINED_MAC_PCS),
    
    // AXI-Stream interface
    .s_axis_tx(s_axis_tx[n]),        // 32-bit Tx
    .m_axis_rx(m_axis_rx[n]),        // 32-bit Rx
    
    // Serdes interface
    .serdes_tx_data(serdes_txdata[n]),   // 64-bit to PHY
    .serdes_rx_data(serdes_rxdata[n])    // 64-bit from PHY
);

// Channel wrapper
taxi_eth_phy_25g_us_ch ch_inst (
    .xcvr_txp(xcvr_txp[n]),
    .xcvr_txn(xcvr_txn[n]),
    .xcvr_rxp(xcvr_rxp[n]),
    .xcvr_rxn(xcvr_rxn[n]),
    
    // 64-bit serdes interface
    .serdes_txdata(serdes_txdata[n]),
    .serdes_rxdata(serdes_rxdata[n])
);
```

---

### 4. MAC/PHY LAYER: `taxi_eth_mac_phy_10g.sv`
**Location**: `src/eth/rtl/taxi_eth_mac_phy_10g.sv`

#### Function:
- 10G Ethernet MAC layer
- PCS layer (if COMBINED_MAC_PCS = 1)
- Handles Ethernet framing, FCS, padding
- Converts between XGMII (32/64-bit) and BASE-R (64B/66B encoding)

#### Signal Flow:

**TX PATH**:
```
AXI-Stream (32-bit @ 156.25 MHz)
    ↓
MAC TX (XGMII 32-bit)
    ↓
XGMII → BASE-R Encoder (64B/66B)
    ↓
Serdes (64-bit @ 156.25 MHz)
```

**RX PATH**:
```
Serdes (64-bit @ 156.25 MHz)
    ↓
BASE-R Decoder (66B/64B) → XGMII
    ↓
MAC RX (XGMII 32-bit)
    ↓
AXI-Stream (32-bit @ 156.25 MHz)
```

#### Key Signals:
```systemverilog
// AXI-Stream interface
input  wire [31:0]  s_axis_tx_tdata  // 32-bit @ 156.25 MHz
output wire [31:0]  m_axis_rx_tdata

// Serdes interface (to PHY)
output wire [63:0]  serdes_tx_data   // 64-bit @ 156.25 MHz
input  wire [63:0]  serdes_rx_data
output wire [1:0]   serdes_tx_hdr    // 2-bit sync header
input  wire [1:0]   serdes_rx_hdr
```

---

### 5. PHY CHANNEL WRAPPER: `taxi_eth_phy_25g_us_ch`
**Inferred from**: Integration in `taxi_eth_mac_25g_us.sv`

#### Function:
- Per-channel wrapper for GTY transceiver
- Contains optional TX/RX pipeline stages
- Handles clock domain interfacing

#### Signal Flow:

**TX PATH**:
```
serdes_txdata[63:0] → Optional Pipeline → gt_txdata[63:0] → GTY Wrapper
```

**RX PATH**:
```
GTY Wrapper → gt_rxdata[63:0] → Optional Pipeline → serdes_rxdata[63:0]
```

---

### 6. GTY TRANSCEIVER WRAPPER: `taxi_eth_phy_10g_us_gt.sv` or `taxi_eth_phy_10g_us_gt_ll.sv`
**Location**: `src/eth/rtl/us/taxi_eth_phy_10g_us_gt_ll.sv` (low latency variant)

#### Function:
- Wraps single GTY channel for 10G operation
- Provides DRP (Dynamic Reconfiguration Port) interface
- Handles GTY reset sequencing and control
- Manages 64B/66B encoding at serdes interface

#### Signal Flow:

**TX PATH**:
```
serdes_txdata[63:0] + 2-bit header → GTY Primitive
```

**RX PATH**:
```
GTY Primitive → serdes_rxdata[63:0] + 2-bit header
```

#### Key Signals:
```systemverilog
// Serial interface
output wire logic xcvr_txp
output wire logic xcvr_txn
input  wire logic xcvr_rxp
input  wire logic xcvr_rxn

// Parallel serdes interface
input  wire [63:0]  serdes_txdata    // 64-bit @ 156.25 MHz
input  wire [1:0]   serdes_txheader  // 2-bit sync header
output wire [63:0]  serdes_rxdata
output wire [1:0]   serdes_rxheader

// Clocking
output wire tx_clk_out               // 156.25 MHz
output wire rx_clk_out               // 156.25 MHz
```

---

### 7. PRIMITIVE LEVEL: GTY Transceiver Primitives
**Type**: Xilinx GTYE4_CHANNEL / GTYE4_COMMON primitives

#### Function:
- Line rate: 10.3125 Gbps (10G Ethernet)
- Reference clock: 156.25 MHz
- User clock: 156.25 MHz (line rate / 66)
- Data width: 64 bits parallel
- Encoding: 64B/66B (64 data bits + 2 sync bits)

#### GTY Configuration for 10G:
```systemverilog
GTYE4_CHANNEL #(
    // 10G line rate configuration
    .TX_INT_DATAWIDTH(0),           // 40-bit internal
    .TX_DATA_WIDTH(64),             // 64-bit user interface
    .RX_INT_DATAWIDTH(0),
    .RX_DATA_WIDTH(64),
    
    // Protocol
    .TX_HEADER_WIDTH(2),            // 64B/66B sync header
    .RX_HEADER_WIDTH(2),
    
    // Line rate: 10.3125 Gbps
    .TXOUT_DIV(1),
    .RXOUT_DIV(1)
) gtye4_channel_inst (
    // Serial I/O
    .GTYTXP(xcvr_txp),
    .GTYTXN(xcvr_txn),
    .GTYRXP(xcvr_rxp),
    .GTYRXN(xcvr_rxn),
    
    // Parallel data
    .TXDATA(serdes_txdata),         // 64-bit @ 156.25 MHz
    .TXHEADER(serdes_txheader),     // 2-bit
    .RXDATA(serdes_rxdata),         // 64-bit @ 156.25 MHz
    .RXHEADER(serdes_rxheader),     // 2-bit
    
    // User clocks
    .TXUSRCLK(tx_clk),              // 156.25 MHz
    .RXUSRCLK(rx_clk),              // 156.25 MHz
    
    // Reference
    .GTREFCLK0(gtrefclk)            // 156.25 MHz
);
```

---

## Complete Signal Path Summary

### TX PATH (Top → Bottom):
```
User Application
    ↓ AXI-Stream 32-bit @ 156.25 MHz (per lane)
fpga_core
    ↓ AXI-Stream 32-bit (8 independent lanes)
taxi_eth_mac_25g_us (×2 quads, 4 lanes each)
    ↓ AXI-Stream 32-bit per lane
taxi_eth_mac_phy_10g (per lane)
    ↓ MAC → XGMII 32-bit → BASE-R Encoder
    ↓ 64-bit + 2-bit header (64B/66B)
taxi_eth_phy_25g_us_ch (per lane)
    ↓ 64-bit + header (with optional pipeline)
taxi_eth_phy_10g_us_gt_ll (per lane)
    ↓ 64-bit + 2-bit header
GTYE4_CHANNEL (Primitive)
    ↓ Serial 10.3125 Gbps
Physical Pins: qsfp[0|1]_tx_p[0:3], qsfp[0|1]_tx_n[0:3]
```

### RX PATH (Bottom → Top):
```
Physical Pins: qsfp[0|1]_rx_p[0:3], qsfp[0|1]_rx_n[0:3]
    ↓ Serial 10.3125 Gbps
GTYE4_CHANNEL (Primitive)
    ↓ 64-bit @ 156.25 MHz + 2-bit header
taxi_eth_phy_10g_us_gt_ll (per lane)
    ↓ 64-bit + 2-bit header (66B/64B)
taxi_eth_phy_25g_us_ch (per lane)
    ↓ 64-bit + header (with optional pipeline)
taxi_eth_mac_phy_10g (per lane)
    ↓ BASE-R Decoder → XGMII 32-bit → MAC
    ↓ AXI-Stream 32-bit per lane
taxi_eth_mac_25g_us (×2 quads, 4 lanes each)
    ↓ AXI-Stream 32-bit (8 independent lanes)
fpga_core
    ↓ AXI-Stream 32-bit @ 156.25 MHz
User Application
```

---

## Key Data Widths and Rates

| Level | TX Data Width | RX Data Width | Clock Frequency | Line Rate |
|-------|--------------|--------------|----------------|-----------|
| Application (fpga_core) | 32-bit/lane | 32-bit/lane | 156.25 MHz | 10 Gbps |
| MAC (taxi_eth_mac_25g_us) | 32-bit/lane | 32-bit/lane | 156.25 MHz | 10 Gbps |
| MAC/PHY (taxi_eth_mac_phy_10g) | 32-bit XGMII | 32-bit XGMII | 156.25 MHz | 10 Gbps |
| Serdes (to PHY) | 64-bit | 64-bit | 156.25 MHz | 10 Gbps |
| GTY Internal | 40-bit | 40-bit | 156.25 MHz | 10.3125 Gbps |
| GTY Serial | 1-bit | 1-bit | 10.3125 GHz | 10.3125 Gbps |

**Note**: Each lane operates independently. With 4 lanes per QSFP port, total throughput is 40 Gbps per port (4 × 10G), but lanes are NOT bonded - each is a separate 10G link.

---

## Comparison: 10G vs 100G Configuration

| Feature | 10G Configuration | 100G Configuration |
|---------|------------------|-------------------|
| MAC_DATA_W | 32 | 512 |
| MAC Module | taxi_eth_mac_25g_us | taxi_eth_mac_100g_us |
| Lanes per Port | 4 (independent) | 4 (bonded) |
| Data per Lane | 32-bit @ 156 MHz | 128-bit @ 322 MHz |
| MAC/PHY Module | taxi_eth_mac_phy_10g | Integrated CMACE4 |
| Encoding | 64B/66B (BASE-R) | 66B/64B (BASE-R) |
| Line Rate per Lane | 10.3125 Gbps | 25.78125 Gbps |
| Total per Port | 40 Gbps (4×10G) | ~100 Gbps (4×25G) |
| Lane Bonding | No (independent) | Yes (via CMAC) |

---

## Module File Locations

| Module | File Path |
|--------|-----------|
| fpga | src/eth/example/Alveo/fpga/rtl/fpga_au280.sv |
| fpga_core | src/eth/example/Alveo/fpga/rtl/fpga_core.sv |
| taxi_eth_mac_25g_us | src/eth/rtl/us/taxi_eth_mac_25g_us.sv |
| taxi_eth_mac_phy_10g | src/eth/rtl/taxi_eth_mac_phy_10g.sv |
| taxi_eth_mac_phy_10g_tx | src/eth/rtl/taxi_eth_mac_phy_10g_tx.sv |
| taxi_eth_mac_phy_10g_rx | src/eth/rtl/taxi_eth_mac_phy_10g_rx.sv |
| taxi_eth_mac_10g | src/eth/rtl/taxi_eth_mac_10g.sv |
| taxi_eth_phy_10g | src/eth/rtl/taxi_eth_phy_10g.sv |
| taxi_eth_phy_10g_us_gt_ll | src/eth/rtl/us/taxi_eth_phy_10g_us_gt_ll.sv |
| taxi_eth_phy_10g_us_gt | src/eth/rtl/us/taxi_eth_phy_10g_us_gt.sv |

---

## Notes

1. **Per-Lane Operation**: Unlike 100G which bonds 4 lanes together, 10G configuration treats each lane as an independent 10G link.

2. **USXGMII Autonegotiation**: The design supports USXGMII (10M/100M/1G/2.5G/5G/10G) autonegotiation for flexible speed adaptation.

3. **Low Latency Mode**: Uses `CFG_LOW_LATENCY = 1'b1` which selects the `_gt_ll` (low latency) variant of the PHY wrapper.

4. **Pipeline Stages**: Optional 1-cycle pipeline stages (`TX_SERDES_PIPELINE = 1`, `RX_SERDES_PIPELINE = 1`) for timing closure.

5. **Data Rate**: Each lane operates at 10.3125 Gbps (10G Ethernet line rate), using 64B/66B encoding (64/66 = ~0.97 efficiency).

6. **QPLL**: Typically QPLL0 is used, providing the reference for all 4 channels in a quad.

7. **Independent Clocks**: Each 10G lane has its own rx_clk and tx_clk at 156.25 MHz, recovered independently.

---

Document generated: 2026-09-12
