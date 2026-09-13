# ZCU106 10G Ethernet - Tx and Rx Signal Path Analysis

This document traces the Ethernet transmit (Tx) and receive (Rx) signal paths from the top-level FPGA module down to the physical GTH transceiver ports for the **Xilinx ZCU106 10G Ethernet configuration**.

## Design Overview

- **Board**: Xilinx ZCU106 Evaluation Board
- **FPGA**: Zynq UltraScale+ MPSoC (XCZU7EV)
- **Ethernet Speed**: 10G per port
- **Transceiver Type**: GTH (Zynq UltraScale+)
- **Ports**: 2 SFP+ cages (SFP0, SFP1)
- **Data Width**: 32-bit internal datapath per port
- **Configuration**: Low latency mode enabled, combined MAC+PCS
- **Encoding**: 64B/66B (BASE-R)

---

## Signal Path Hierarchy

### 1. TOP LEVEL: `fpga.sv` (fpga)

**Location**: `src/eth/example/ZCU106/fpga/rtl/fpga.sv`

#### Configuration:

```systemverilog
parameter MAC_DATA_W = 32           // 10G configuration (32-bit datapath)
parameter CFG_LOW_LATENCY = 1'b1    // Low latency mode
parameter COMBINED_MAC_PCS = 1'b1   // Integrated MAC+PCS
parameter FAMILY = "zynquplus"      // Zynq UltraScale+
```

#### Port Signals:

```systemverilog
// SFP+ Interfaces (2 ports)
input  wire logic sfp_rx_p[2]       // Rx differential positive
input  wire logic sfp_rx_n[2]       // Rx differential negative
output wire logic sfp_tx_p[2]       // Tx differential positive
output wire logic sfp_tx_n[2]       // Tx differential negative

// Reference clock (156.25 MHz)
input  wire logic sfp_mgt_refclk_0_p
input  wire logic sfp_mgt_refclk_0_n

// Control
output wire logic [1:0] sfp_tx_disable_b  // Tx enable (active high)
```

#### Clocking:

```systemverilog
// System clocks from on-board 125 MHz oscillator
input  wire logic clk_125mhz_p      // 125 MHz LVDS input
input  wire logic clk_125mhz_n

// MMCM generates:
wire clk_125mhz_int                 // 125 MHz system clock
wire clk_62mhz_int                  // 62.5 MHz (unused)
```

#### Module Instantiation:

```systemverilog
fpga_core #(
    .FAMILY(FAMILY),
    .CFG_LOW_LATENCY(CFG_LOW_LATENCY),
    .COMBINED_MAC_PCS(COMBINED_MAC_PCS),
    .MAC_DATA_W(MAC_DATA_W)
) core_inst (
    .clk_125mhz(clk_125mhz_int),
    .rst_125mhz(rst_125mhz_int),
    
    // SFP+ interfaces
    .sfp_rx_p(sfp_rx_p),
    .sfp_rx_n(sfp_rx_n),
    .sfp_tx_p(sfp_tx_p),
    .sfp_tx_n(sfp_tx_n),
    .sfp_mgt_refclk_0_p(sfp_mgt_refclk_0_p),
    .sfp_mgt_refclk_0_n(sfp_mgt_refclk_0_n),
    .sfp_tx_disable_b(sfp_tx_disable_b)
);
```

---

### 2. CORE LEVEL: `fpga_core.sv`

**Location**: `src/eth/example/ZCU106/fpga/rtl/fpga_core.sv`

#### Configuration:

```systemverilog
parameter MAC_DATA_W = 32           // 32-bit per port for 10G
parameter FAMILY = "zynquplus"      // GTH transceivers
```

#### Key Signals:

```systemverilog
// From top level (2 SFP+ ports)
input  wire logic sfp_rx_p[2]
input  wire logic sfp_rx_n[2]
output wire logic sfp_tx_p[2]
output wire logic sfp_tx_n[2]

// MAC interface (per port)
wire sfp_tx_clk[2]                  // MAC Tx clock per port
wire sfp_tx_rst[2]                  // MAC Tx reset per port
taxi_axis_if axis_sfp_tx[2]         // AXI-Stream Tx data (32-bit per port)
taxi_axis_if axis_sfp_tx_cpl[2]     // AXI-Stream Tx completion
wire sfp_rx_clk[2]                  // MAC Rx clock per port
wire sfp_rx_rst[2]                  // MAC Rx reset per port
taxi_axis_if axis_sfp_rx[2]         // AXI-Stream Rx data (32-bit per port)

wire sfp_rx_status[2]               // Link status per port
wire sfp_gtpowergood                // GTH power good

// Reference clock
wire sfp_mgt_refclk_0               // 156.25 MHz from IBUFDS_GTE4
wire sfp_mgt_refclk_0_int           // ODIV2 output
wire sfp_mgt_refclk_0_bufg          // Through BUFG_GT
```

#### Clock Generation:

```systemverilog
// Reference clock buffer (GTH specific)
IBUFDS_GTE4 ibufds_gte4_sfp_mgt_refclk_0_inst (
    .I     (sfp_mgt_refclk_0_p),
    .IB    (sfp_mgt_refclk_0_n),
    .CEB   (1'b0),
    .O     (sfp_mgt_refclk_0),          // To GTH
    .ODIV2 (sfp_mgt_refclk_0_int)       // /2 output
);

// Clock buffer
BUFG_GT bufg_gt_sfp_mgt_refclk_0_inst (
    .CE      (sfp_gtpowergood),
    .I       (sfp_mgt_refclk_0_int),
    .O       (sfp_mgt_refclk_0_bufg)    // To logic
);
```

#### Module Instantiation:

Since `MAC_DATA_W == 32` (not 16):

```systemverilog
taxi_eth_mac_25g_us sfp_mac_inst (
    .CNT(2),                            // 2 SFP+ ports
    .DATA_W(32),                        // 32-bit datapath (10G)
    .USXGMII_EN(1),                     // Enable USXGMII autonegotiation
    .GT_TYPE("GTH"),                    // GTH transceivers (not GTY)
    .FAMILY("zynquplus"),
    .COMBINED_MAC_PCS(COMBINED_MAC_PCS),
    .CFG_LOW_LATENCY(CFG_LOW_LATENCY),
    
    // Control
    .xcvr_ctrl_clk(clk_125mhz),
    .xcvr_ctrl_rst(sfp_rst),
    
    // Serial interface (2 ports)
    .xcvr_txp(sfp_tx_p),
    .xcvr_txn(sfp_tx_n),
    .xcvr_rxp(sfp_rx_p),
    .xcvr_rxn(sfp_rx_n),
    
    // Reference clock
    .xcvr_gtrefclk00_in(sfp_mgt_refclk_0),
    .xcvr_gtrefclk01_in(sfp_mgt_refclk_0),
    
    // Parallel interface (array of 2)
    .s_axis_tx(axis_sfp_tx),            // 32-bit Tx per port
    .m_axis_rx(axis_sfp_rx),            // 32-bit Rx per port
    .rx_clk(sfp_rx_clk),                // Per-port rx clock
    .tx_clk(sfp_tx_clk),                // Per-port tx clock
    .rx_status(sfp_rx_status)           // Link status
);
```

---

### 3. MAC/PHY WRAPPER: `taxi_eth_mac_25g_us.sv`

**Location**: `src/eth/rtl/us/taxi_eth_mac_25g_us.sv`

This is the same module used in U280, but configured for:

- **CNT = 2** (2 channels/ports instead of 4)
- **GT_TYPE = "GTH"** (instead of "GTY")
- **FAMILY = "zynquplus"**

#### Function:

- Wraps CNT (2) GTH channels
- Each channel operates independently at 10G
- Provides per-port 32-bit parallel interface
- Handles USXGMII autonegotiation

#### Key Parameters:

```systemverilog
parameter CNT = 2                    // 2 channels for ZCU106
parameter DATA_W = 32                // 32-bit for 10G
parameter GT_TYPE = "GTH"            // GTH (not GTY)
parameter COMBINED_MAC_PCS = 1       // Integrated MAC+PCS
parameter USXGMII_EN = 1             // Enable USXGMII autonegotiation
parameter TX_SERDES_PIPELINE = 1     // 1-cycle Tx pipeline
parameter RX_SERDES_PIPELINE = 1     // 1-cycle Rx pipeline
parameter COUNT_125US = 125000/6.4   // Timeout counter
```

#### Signal Flow:

**TX PATH** (per channel):

```
AXI-Stream Input (32-bit @ 156.25 MHz)
    ↓
MAC → PCS → PHY
    ↓
64-bit Serdes
    ↓
GTH Channel
```

**RX PATH** (per channel):

```
GTH Channel
    ↓
64-bit Serdes
    ↓
PHY → PCS → MAC
    ↓
AXI-Stream Output (32-bit @ 156.25 MHz)
```

#### Module Instantiation:

For each channel (n=0,1):

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

**Same as U280** - See U280 documentation for details.

#### Function:

- 10G Ethernet MAC layer
- PCS layer (64B/66B encoding)
- Handles Ethernet framing, FCS, padding
- Converts between XGMII (32-bit) and BASE-R

#### Key Components:

- `taxi_eth_mac_10g`: MAC layer with XGMII interface
- `taxi_axis_baser_tx_32`: TX BASE-R encoder (32-bit → 64-bit)
- `taxi_axis_baser_rx_32`: RX BASE-R decoder (64-bit → 32-bit)
- `taxi_eth_phy_10g`: PHY layer with serdes interface

---

### 5. PHY CHANNEL WRAPPER: `taxi_eth_phy_25g_us_ch`

**Inferred from**: Integration in `taxi_eth_mac_25g_us.sv`

**Same structure as U280**, but instantiates GTH-specific modules.

#### Function:

- Per-channel wrapper for GTH transceiver
- Contains optional TX/RX pipeline stages
- Selects between low-latency and standard GTH variants

---

### 6. GTH TRANSCEIVER WRAPPER: `taxi_eth_phy_10g_us_gt_ll.sv`

**Location**: `src/eth/rtl/us/taxi_eth_phy_10g_us_gt_ll.sv`

#### Function:

- Wraps single GTH channel for 10G operation
- Provides DRP (Dynamic Reconfiguration Port) interface
- Handles GTH reset sequencing and control
- Manages 64B/66B encoding at serdes interface

#### Key Differences from GTY:

- Uses **GTHE4_CHANNEL** primitives (instead of GTYE4)
- Uses **GTHE4_COMMON** for QPLL (instead of GTYE4_COMMON)
- Different DRP address map
- Slightly different reset sequencing

#### Signal Flow:

**TX PATH**:
```
serdes_txdata[63:0] + 2-bit header → GTHE4_CHANNEL
```

**RX PATH**:
```
GTHE4_CHANNEL → serdes_rxdata[63:0] + 2-bit header
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
input  wire xcvr_gtrefclk00_in       // 156.25 MHz reference
```

---

### 7. PRIMITIVE LEVEL: GTH Transceiver Primitives

**Type**: Xilinx GTHE4_CHANNEL / GTHE4_COMMON primitives

#### Function:

- Line rate: 10.3125 Gbps (10G Ethernet)
- Reference clock: 156.25 MHz
- User clock: 156.25 MHz (line rate / 66)
- Data width: 64 bits parallel
- Encoding: 64B/66B (64 data bits + 2 sync bits)

#### GTH vs GTY Differences:

| Feature | GTH (ZCU106) | GTY (U280) |
|---------|-------------|-----------|
| Max Line Rate | 16.3 Gbps | 32.75 Gbps |
| FPGA Family | Zynq UltraScale+ | UltraScale+ |
| Primitive | GTHE4_CHANNEL | GTYE4_CHANNEL |
| Common | GTHE4_COMMON | GTYE4_COMMON |
| Power | Lower | Higher performance |

#### GTH Configuration for 10G:

```systemverilog
GTHE4_CHANNEL #(
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
) gthe4_channel_inst (
    // Serial I/O
    .GTHTXP(xcvr_txp),
    .GTHTXN(xcvr_txn),
    .GTHRXP(xcvr_rxp),
    .GTHRXN(xcvr_rxn),
    
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
    ↓ AXI-Stream 32-bit @ 156.25 MHz (per port)
fpga_core
    ↓ AXI-Stream 32-bit (2 independent ports)
taxi_eth_mac_25g_us (CNT=2)
    ↓ AXI-Stream 32-bit per port
taxi_eth_mac_phy_10g (per port)
    ↓ MAC → XGMII 32-bit → BASE-R Encoder
    ↓ 64-bit + 2-bit header (64B/66B)
taxi_eth_phy_25g_us_ch (per port)
    ↓ 64-bit + header (with optional pipeline)
taxi_eth_phy_10g_us_gt_ll (per port)
    ↓ 64-bit + 2-bit header
GTHE4_CHANNEL (Primitive)
    ↓ Serial 10.3125 Gbps
Physical Pins: sfp_tx_p[0:1], sfp_tx_n[0:1]
```

### RX PATH (Bottom → Top):

```
Physical Pins: sfp_rx_p[0:1], sfp_rx_n[0:1]
    ↓ Serial 10.3125 Gbps
GTHE4_CHANNEL (Primitive)
    ↓ 64-bit @ 156.25 MHz + 2-bit header
taxi_eth_phy_10g_us_gt_ll (per port)
    ↓ 64-bit + 2-bit header (66B/64B)
taxi_eth_phy_25g_us_ch (per port)
    ↓ 64-bit + header (with optional pipeline)
taxi_eth_mac_phy_10g (per port)
    ↓ BASE-R Decoder → XGMII 32-bit → MAC
    ↓ AXI-Stream 32-bit per port
taxi_eth_mac_25g_us (CNT=2)
    ↓ AXI-Stream 32-bit (2 independent ports)
fpga_core
    ↓ AXI-Stream 32-bit @ 156.25 MHz
User Application
```

---

## Key Data Widths and Rates

| Level | TX Data Width | RX Data Width | Clock Frequency | Line Rate |
|-------|--------------|--------------|----------------|-----------|
| Application (`fpga_core`) | 32-bit/port | 32-bit/port | 156.25 MHz | 10 Gbps |
| MAC (`taxi_eth_mac_25g_us`) | 32-bit/port | 32-bit/port | 156.25 MHz | 10 Gbps |
| MAC/PHY (`taxi_eth_mac_phy_10g`) | 32-bit XGMII | 32-bit XGMII | 156.25 MHz | 10 Gbps |
| Serdes (to PHY) | 64-bit | 64-bit | 156.25 MHz | 10 Gbps |
| GTH Internal | 40-bit | 40-bit | 156.25 MHz | 10.3125 Gbps |
| GTH Serial | 1-bit | 1-bit | 10.3125 GHz | 10.3125 Gbps |

**Note**: Each SFP+ port operates as an independent 10G link.

---

## Comparison: ZCU106 vs U280 10G

| Feature | ZCU106 | U280 |
|---------|--------|------|
| FPGA | Zynq UltraScale+ MPSoC | UltraScale+ FPGA |
| Transceiver | GTH (GTHE4) | GTY (GTYE4) |
| Max GT Rate | 16.3 Gbps | 32.75 Gbps |
| Form Factor | SFP+ (2 ports) | QSFP28 (2 ports, 4 lanes each) |
| Ports Used | 2 (SFP0, SFP1) | 8 lanes (can be 8×10G) |
| Ref Clock | 156.25 MHz | 156.25 MHz |
| MAC Module | `taxi_eth_mac_25g_us` (CNT=2) | `taxi_eth_mac_25g_us` (CNT=4) |
| System Clock | 125 MHz on-board osc | 156.25 MHz from GTY |
| Application | Evaluation/Development | Data Center Acceleration |

---

## Module File Locations

| Module | File Path |
|--------|-----------|
| `fpga` | `src/eth/example/ZCU106/fpga/rtl/fpga.sv` |
| `fpga_core` | `src/eth/example/ZCU106/fpga/rtl/fpga_core.sv` |
| `taxi_eth_mac_25g_us` | `src/eth/rtl/us/taxi_eth_mac_25g_us.sv` |
| `taxi_eth_mac_phy_10g` | `src/eth/rtl/taxi_eth_mac_phy_10g.sv` |
| `taxi_eth_mac_phy_10g_tx` | `src/eth/rtl/taxi_eth_mac_phy_10g_tx.sv` |
| `taxi_eth_mac_phy_10g_rx` | `src/eth/rtl/taxi_eth_mac_phy_10g_rx.sv` |
| `taxi_eth_mac_10g` | `src/eth/rtl/taxi_eth_mac_10g.sv` |
| `taxi_eth_phy_10g` | `src/eth/rtl/taxi_eth_phy_10g.sv` |
| `taxi_eth_phy_10g_us_gt_ll` | `src/eth/rtl/us/taxi_eth_phy_10g_us_gt_ll.sv` |
| `taxi_eth_phy_10g_us_gt` | `src/eth/rtl/us/taxi_eth_phy_10g_us_gt.sv` |

---

## Board-Specific Details

### ZCU106 SFP+ Cages:

- **Location**: On-board, readily accessible
- **SFP0**: GTH Quad 130, Channel 0
- **SFP1**: GTH Quad 130, Channel 1
- **Reference Clock**: Shared 156.25 MHz clock to both channels

### Power Supplies:

- **VCC_PSINTFP** (PS)
- **MGTAVCC** (GTH analog supply, 0.9V)
- **MGTAVTT** (GTH termination, 1.2V)

### Additional I/O:

- **GPIO**: Buttons, switches, LEDs for debug
- **UART**: 115200 bps for XFCP control interface

---

## Notes

1. **GTH vs GTY**: ZCU106 uses GTH transceivers which are optimized for lower power and cost, with max line rate of 16.3 Gbps (sufficient for 10G). U280 uses GTY for higher performance applications up to 32.75 Gbps.

2. **Independent Ports**: Each SFP+ port operates as a completely independent 10G Ethernet link with its own clock domain.

3. **USXGMII Autonegotiation**: Supports autonegotiation for flexible speeds: 10M/100M/1G/2.5G/5G/10G.

4. **Zynq Integration**: The design can be easily integrated with Zynq PS (Processing System) for ARM-based control and data processing.

5. **Low Latency Mode**: Uses `CFG_LOW_LATENCY = 1'b1` for minimal latency through the datapath.

6. **Clock Architecture**: 
   - System clock: 125 MHz (on-board oscillator)
   - GTH reference: 156.25 MHz (from SFP+ module or on-board source)
   - MAC user clocks: 156.25 MHz (recovered per port)

7. **XFCP**: UART-based control interface for configuration and statistics access.

---

Document generated: 2026-09-12
