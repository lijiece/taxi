# Ethernet Signal Path Documentation Summary

This directory contains comprehensive signal path analyses for three Ethernet configurations across two FPGA platforms.

## Documentation Files

### 1. U280_100G_TX_RX_SIGNAL_PATH.md
**Configuration**: Alveo AU280 - 100G Ethernet

- **Speed**: 100 Gbps per port (4×25G bonded)
- **Transceiver**: GTY (GTYE4)
- **Ports**: 2 QSFP28 ports
- **Data Width**: 512-bit parallel datapath
- **MAC Module**: `taxi_eth_mac_100g_us`
- **Key Feature**: Lane bonding via Xilinx CMACE4 IP
- **Line Rate**: 25.78125 Gbps per lane
- **Encoding**: 66B/64B (BASE-R with RS-FEC)

### 2. U280_10G_TX_RX_SIGNAL_PATH.md
**Configuration**: Alveo AU280 - 10G Ethernet

- **Speed**: 10 Gbps per lane (independent)
- **Transceiver**: GTY (GTYE4)
- **Ports**: 2 QSFP28 ports (4 lanes each)
- **Data Width**: 32-bit parallel datapath per lane
- **MAC Module**: `taxi_eth_mac_25g_us`
- **Key Feature**: Independent per-lane operation
- **Line Rate**: 10.3125 Gbps per lane
- **Encoding**: 64B/66B (BASE-R)

### 3. ZCU106_10G_TX_RX_SIGNAL_PATH.md
**Configuration**: Xilinx ZCU106 - 10G Ethernet

- **Speed**: 10 Gbps per port (independent)
- **Transceiver**: GTH (GTHE4)
- **Ports**: 2 SFP+ cages
- **Data Width**: 32-bit parallel datapath per port
- **MAC Module**: `taxi_eth_mac_25g_us`
- **Key Feature**: Zynq UltraScale+ integration
- **Line Rate**: 10.3125 Gbps per port
- **Encoding**: 64B/66B (BASE-R)

---

## Architecture Comparison

### Platform Comparison

| Feature | U280 (100G) | U280 (10G) | ZCU106 (10G) |
|---------|-------------|------------|--------------|
| **FPGA** | UltraScale+ | UltraScale+ | Zynq UltraScale+ MPSoC |
| **Part** | XCU280 | XCU280 | XCZU7EV |
| **Transceiver** | GTY (GTYE4) | GTY (GTYE4) | GTH (GTHE4) |
| **Max GT Rate** | 32.75 Gbps | 32.75 Gbps | 16.3 Gbps |
| **Form Factor** | QSFP28 | QSFP28 | SFP+ |
| **Ports** | 2 (bonded) | 2×4 (independent) | 2 (independent) |

### Configuration Comparison

| Parameter | U280 (100G) | U280 (10G) | ZCU106 (10G) |
|-----------|-------------|------------|--------------|
| **MAC_DATA_W** | 512 | 32 | 32 |
| **MAC Module** | taxi_eth_mac_100g_us | taxi_eth_mac_25g_us | taxi_eth_mac_25g_us |
| **Lanes/Port** | 4 (bonded) | 4 (independent) | 1 |
| **Speed/Lane** | 25G | 10G | 10G |
| **Total/Port** | ~100 Gbps | 40 Gbps (4×10G) | 10 Gbps |
| **User Clock** | 322.265625 MHz | 156.25 MHz | 156.25 MHz |
| **Line Rate** | 25.78125 Gbps | 10.3125 Gbps | 10.3125 Gbps |
| **CMAC IP** | Yes (CMACE4) | No | No |
| **Encoding** | 66B/64B + RS-FEC | 64B/66B | 64B/66B |

---

## Signal Path Depth Comparison

### U280 100G Configuration
```
7 levels from application to pins:
fpga_au280 → fpga_core → taxi_eth_mac_100g_us → 
taxi_eth_mac_100g_us_ch → taxi_eth_mac_100g_us_gt_ll → 
taxi_eth_phy_25g_us_gt_ll → GTYE4_CHANNEL
```

### U280 10G Configuration
```
6-7 levels from application to pins:
fpga_au280 → fpga_core → taxi_eth_mac_25g_us → 
taxi_eth_mac_phy_10g → taxi_eth_phy_10g_us_gt_ll → 
GTYE4_CHANNEL
```

### ZCU106 10G Configuration
```
6-7 levels from application to pins:
fpga → fpga_core → taxi_eth_mac_25g_us → 
taxi_eth_mac_phy_10g → taxi_eth_phy_10g_us_gt_ll → 
GTHE4_CHANNEL
```

---

## Key Module Roles

### Top-Level Modules
- **fpga_au280.sv** / **fpga.sv**: Top-level with physical I/O
- **fpga_core.sv**: Core logic with MAC instantiation

### MAC Layer Modules
- **taxi_eth_mac_100g_us**: 100G MAC with CMAC integration (512-bit)
- **taxi_eth_mac_25g_us**: Multi-rate MAC (10G/25G, 32/64-bit)
- **taxi_eth_mac_phy_10g**: 10G MAC+PCS layer
- **taxi_eth_mac_10g**: 10G MAC only (XGMII interface)

### PHY Layer Modules
- **taxi_eth_phy_10g**: 10G PHY with BASE-R encoding
- **taxi_eth_phy_25g_us_gt_ll**: 25G PHY wrapper (low latency)
- **taxi_eth_phy_10g_us_gt_ll**: 10G PHY wrapper (low latency)

### Transceiver Wrappers
- **taxi_eth_mac_100g_us_ch**: 100G per-channel wrapper
- **taxi_eth_mac_25g_us_ch**: 10G/25G per-channel wrapper (inferred)

---

## Data Path Widths

### U280 100G
```
Application: 512-bit
    ↓
CMAC: 512-bit → split to 4×128-bit
    ↓
Per Lane: 128-bit @ 322 MHz
    ↓
GTY Internal: 80-bit
    ↓
Serial: 25.78125 Gbps
```

### U280/ZCU106 10G
```
Application: 32-bit per lane
    ↓
MAC: XGMII 32-bit
    ↓
BASE-R: 64-bit @ 156 MHz
    ↓
GTY/GTH Internal: 40-bit
    ↓
Serial: 10.3125 Gbps
```

---

## Clock Domains

### U280 100G
- **System Clock**: 125 MHz (from GTY ref clock)
- **GTY Reference**: 156.25 MHz
- **User Clock**: 322.265625 MHz (recovered)
- **All 4 lanes**: Synchronous (bonded)

### U280 10G
- **System Clock**: 125 MHz (from GTY ref clock)
- **GTY Reference**: 156.25 MHz
- **User Clock**: 156.25 MHz per lane (independent)
- **Each lane**: Independent clock domain

### ZCU106 10G
- **System Clock**: 125 MHz (on-board oscillator)
- **GTH Reference**: 156.25 MHz (SFP+ module)
- **User Clock**: 156.25 MHz per port (independent)
- **Each port**: Independent clock domain

---

## Use Cases

### U280 100G
- **Target**: High-throughput data center applications
- **Applications**: Network acceleration, packet processing, 100G switching
- **Advantages**: Maximum throughput, single logical interface
- **Limitations**: Higher resource usage, more complex

### U280 10G
- **Target**: Multi-tenant / multi-stream applications
- **Applications**: 4×10G independent links, flexible port allocation
- **Advantages**: Independent lanes, simpler per-lane logic
- **Limitations**: No lane bonding, lower per-port throughput

### ZCU106 10G
- **Target**: Evaluation and development
- **Applications**: Embedded networking, ARM+FPGA integration
- **Advantages**: Lower cost, Zynq PS integration, SFP+ flexibility
- **Limitations**: GTH max rate (16.3 Gbps), 2 ports only

---

## Key Takeaways

1. **Same Top-Level Files**: Both U280 configurations share the same top-level files (fpga_au280.sv, fpga_core.sv) but are parameterized differently (MAC_DATA_W = 512 vs 32).

2. **Module Reuse**: The taxi_eth_mac_25g_us module is used in both 10G configurations (U280 and ZCU106) with different CNT and GT_TYPE parameters.

3. **Transceiver Differences**: 
   - GTY (U280): Higher performance, up to 32.75 Gbps
   - GTH (ZCU106): Lower power, up to 16.3 Gbps

4. **Lane Bonding**: Only 100G configuration uses lane bonding (via CMAC). 10G configurations have independent lanes/ports.

5. **Clock Architecture**: 
   - 100G: Single synchronous clock domain at 322 MHz
   - 10G: Independent clock domains per lane/port at 156 MHz

6. **Complexity Trade-offs**:
   - 100G: Higher complexity, integrated CMAC IP, maximum throughput
   - 10G: Simpler logic, no proprietary IP, flexible independent lanes

---

## Common Modules Across All Configurations

These modules are shared across all three configurations:

- **taxi_eth_mac_phy_10g**: 10G MAC+PHY layer
- **taxi_eth_mac_10g**: 10G MAC
- **taxi_eth_phy_10g**: 10G PHY  
- **taxi_eth_phy_10g_rx/tx**: 10G RX/TX PHY
- **taxi_axis_baser_tx/rx**: BASE-R encoder/decoder
- **taxi_xgmii_baser_enc/dec**: XGMII/BASE-R conversion

This demonstrates excellent design reuse in the Taxi framework.

---

Document generated: 2026-09-12
