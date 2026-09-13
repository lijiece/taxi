# Ethernet Design Documentation Index

This is the master index for all Ethernet signal path and interface documentation.

---

## Quick Navigation

### Signal Path Analysis
1. **[U280 100G Configuration](U280_100G_TX_RX_SIGNAL_PATH.md)** - High-throughput bonded lanes
2. **[U280 10G Configuration](U280_10G_TX_RX_SIGNAL_PATH.md)** - Independent multi-lane
3. **[ZCU106 10G Configuration](ZCU106_10G_TX_RX_SIGNAL_PATH.md)** - Zynq UltraScale+ evaluation

### Interface & Protocol Reference
4. **[Critical Interfaces and Protocols](CRITICAL_INTERFACES_AND_PROTOCOLS.md)** - Complete interface guide

### Comparison & Summary
5. **[Signal Path Documentation Summary](SIGNAL_PATH_DOCUMENTATION_SUMMARY.md)** - Cross-platform comparison

---

## Document Descriptions

### 1. U280_100G_TX_RX_SIGNAL_PATH.md
**Size**: 13 KB | **Complexity**: High

Traces the complete signal path for 100G Ethernet on Alveo AU280:
- **Architecture**: 512-bit datapath with 4×25G bonded lanes
- **Key Technology**: Xilinx CMACE4 IP for 100G MAC
- **Transceivers**: GTY (GTYE4_CHANNEL)
- **Encoding**: 66B/64B with RS-FEC
- **Target Audience**: High-performance networking applications

**Key Sections**:
- 7-level hierarchy (fpga → GTY primitive)
- CMAC integration and lane bonding
- 322 MHz clock domain details
- Complete module instantiation examples

---

### 2. U280_10G_TX_RX_SIGNAL_PATH.md
**Size**: 14 KB | **Complexity**: Medium

Analyzes 10G Ethernet configuration on the same U280 platform:
- **Architecture**: 32-bit datapath per lane, 8 independent lanes
- **Comparison**: Details differences from 100G configuration
- **MAC Module**: taxi_eth_mac_25g_us (no CMAC IP)
- **Flexibility**: Each lane operates as independent 10G link

**Key Sections**:
- Per-lane architecture (4 lanes per QSFP28 port)
- Independent clock domains @ 156 MHz
- BASE-R (64B/66B) encoding without RS-FEC
- Side-by-side 10G vs 100G comparison table

---

### 3. ZCU106_10G_TX_RX_SIGNAL_PATH.md
**Size**: 16 KB | **Complexity**: Medium

Documents 10G Ethernet on Zynq UltraScale+ evaluation board:
- **Platform**: Xilinx ZCU106 with XCZU7EV MPSoC
- **Form Factor**: 2 SFP+ cages (not QSFP28)
- **Transceivers**: GTH (GTHE4) instead of GTY
- **Integration**: Zynq PS + PL combined system

**Key Sections**:
- GTH vs GTY transceiver differences
- SFP+ cage pin mappings
- Zynq-specific clock architecture
- Board-level integration details

---

### 4. CRITICAL_INTERFACES_AND_PROTOCOLS.md
**Size**: 20 KB | **Complexity**: High | **Type**: Reference

Comprehensive guide to all interfaces and protocols used in the design:

#### Major Interfaces Covered:
1. **AXI-Stream (AXIS)** - Application data path
   - Signal definitions, flow control, packet format
   - Width variants (32/64/128/512-bit)
   - Taxi-specific extensions (tid, tuser, etc.)

2. **XGMII** - MAC/PCS boundary
   - 32-bit and 64-bit variants
   - Control/data encoding
   - Packet examples with timing

3. **BASE-R (64B/66B)** - PCS encoding
   - Sync header format (01/10)
   - Data vs control blocks
   - Scrambling polynomial
   - 64B/66B vs 66B/64B terminology

4. **Serdes Interface** - PCS/Transceiver boundary
   - 10G: 64-bit @ 156 MHz
   - 25G: 128-bit @ 322 MHz
   - Pipeline stage options

5. **APB** - Control bus
   - AMBA APB protocol
   - DRP (Dynamic Reconfiguration Port) access
   - Transaction timing diagrams

6. **XFCP** - System control protocol
   - UART-based control interface
   - Statistics collection
   - Runtime configuration

7. **USXGMII** - Multi-rate autonegotiation
   - Speed support: 10M to 10G
   - Autonegotiation process
   - Control code format

**Additional Topics**:
- RS-FEC (for 100G)
- Flow Control (PAUSE, PFC)
- PTP timestamping
- Latency analysis
- Clock domain crossings
- Best practices

---

### 5. SIGNAL_PATH_DOCUMENTATION_SUMMARY.md
**Size**: 7.1 KB | **Complexity**: Low | **Type**: Overview

High-level comparison document that synthesizes information across all three configurations:

#### Comparison Tables:
- **Platform Comparison**: FPGA parts, transceivers, form factors
- **Configuration Comparison**: Data widths, speeds, modules
- **Signal Path Depth**: Hierarchy levels for each config
- **Clock Domains**: Frequencies and synchronization

#### Content Highlights:
- Module roles and responsibilities
- Common modules across configurations
- Data path width progressions
- Use case recommendations
- Key takeaways and design insights

**Best Used For**: Quick reference, architecture decisions, design trade-offs

---

## Reading Recommendations

### For Different Audiences:

#### Hardware Engineers (New to Design)
**Start Here**: 
1. Read [Signal Path Summary](SIGNAL_PATH_DOCUMENTATION_SUMMARY.md) first
2. Choose platform: [U280 10G](U280_10G_TX_RX_SIGNAL_PATH.md) or [ZCU106](ZCU106_10G_TX_RX_SIGNAL_PATH.md)
3. Deep dive: [Interfaces & Protocols](CRITICAL_INTERFACES_AND_PROTOCOLS.md)

#### Experienced Ethernet Developers
**Start Here**:
1. Skim [Interfaces & Protocols](CRITICAL_INTERFACES_AND_PROTOCOLS.md) for Taxi-specific details
2. Jump to target platform document
3. Reference [Signal Path Summary](SIGNAL_PATH_DOCUMENTATION_SUMMARY.md) for comparisons

#### System Architects
**Start Here**:
1. Read [Signal Path Summary](SIGNAL_PATH_DOCUMENTATION_SUMMARY.md)
2. Compare all three configurations side-by-side
3. Focus on "Use Cases" and "Key Takeaways" sections

#### Software/Embedded Engineers
**Start Here**:
1. [ZCU106 document](ZCU106_10G_TX_RX_SIGNAL_PATH.md) - shows Zynq PS integration
2. [Interfaces & Protocols](CRITICAL_INTERFACES_AND_PROTOCOLS.md) - focus on XFCP and control interfaces
3. AXI-Stream sections for data plane interaction

---

## Key Concepts by Topic

### Understanding Data Paths
```
Documents: All signal path docs
Key Sections:
  - "Signal Path Hierarchy" in each platform doc
  - "Data Path Widths" in Summary
  - "Data Flow" diagrams
```

### Transceiver Configuration
```
Documents: Platform-specific docs + Interfaces doc
Key Sections:
  - "GTY/GTH WRAPPER" levels (5-6)
  - "PRIMITIVE LEVEL" sections
  - APB/DRP sections in Interfaces doc
```

### Clock Architecture
```
Documents: All docs
Key Sections:
  - "Clocking" in each platform doc
  - "Clock Domains" in Summary
  - "Clock Domain Crossings" in Interfaces doc
```

### Protocol Details
```
Document: CRITICAL_INTERFACES_AND_PROTOCOLS.md
Sections: Individual protocol sections (1-8)
```

### Performance Tuning
```
Documents: All docs
Key Sections:
  - "Pipeline Stages" mentions
  - "Performance Considerations" in Interfaces doc
  - "Latency Sources" table
  - "Best Practices"
```

---

## Module Cross-Reference

### Top-Level Modules
| Module | Used In | Document Section |
|--------|---------|-----------------|
| fpga_au280.sv | U280 (both) | Level 1 |
| fpga.sv | ZCU106 | Level 1 |
| fpga_core.sv | All platforms | Level 2 |

### MAC Wrappers
| Module | Used In | Data Width | Document Section |
|--------|---------|-----------|-----------------|
| taxi_eth_mac_100g_us | U280 100G | 512-bit | Level 3 |
| taxi_eth_mac_25g_us | U280 10G, ZCU106 | 32/64-bit | Level 3 |

### MAC/PHY Layer
| Module | Used In | Document Section |
|--------|---------|-----------------|
| taxi_eth_mac_phy_10g | 10G configs | Level 4 |
| CMACE4 (Xilinx IP) | U280 100G | Level 3 (internal) |

### PHY Wrappers
| Module | Transceiver | Document Section |
|--------|------------|-----------------|
| taxi_eth_phy_25g_us_gt_ll | GTY | U280 docs, Level 6 |
| taxi_eth_phy_10g_us_gt_ll | GTY/GTH | All 10G docs, Level 6 |

---

## Glossary of Terms

**AXI-Stream**: ARM AMBA streaming interface for packet data  
**BASE-R**: IEEE 802.3 PCS encoding (64B/66B)  
**CMAC**: 100G Ethernet Subsystem (Xilinx IP)  
**DRP**: Dynamic Reconfiguration Port (transceiver config)  
**GTH**: UltraScale+ transceiver (up to 16.3 Gbps)  
**GTY**: UltraScale+ transceiver (up to 32.75 Gbps)  
**MAC**: Media Access Control layer  
**PCS**: Physical Coding Sublayer  
**PHY**: Physical Layer  
**QSFP28**: Quad Small Form-factor Pluggable (4×25G)  
**Serdes**: Serializer/Deserializer  
**SFP+**: Small Form-factor Pluggable Plus (10G)  
**USXGMII**: Universal Serial 10G Media Independent Interface  
**XFCP**: Extensible FPGA Control Platform  
**XGMII**: 10 Gigabit Media Independent Interface  

---

## Document Interconnections

```
                    DOCUMENTATION_INDEX.md (you are here)
                              │
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
    U280_100G_TX_RX    U280_10G_TX_RX   ZCU106_10G_TX_RX
         SIGNAL_PATH.md    SIGNAL_PATH.md   SIGNAL_PATH.md
              │               │               │
              └───────────────┼───────────────┘
                              ↓
              SIGNAL_PATH_DOCUMENTATION_SUMMARY.md
                    (Cross-platform comparison)
                              ↓
              CRITICAL_INTERFACES_AND_PROTOCOLS.md
                    (Technical reference)
```

**Arrows indicate**: "References" or "Provides context for"

---

## Maintenance Notes

### Document Versions
- **Created**: 2026-09-12
- **Platform**: Taxi Ethernet framework
- **Hardware**: Alveo AU280, Xilinx ZCU106
- **Tool Version**: Vivado 2023.x+

### Update Procedures
When updating these documents:
1. Update individual platform docs first
2. Regenerate Summary doc with new comparisons
3. Update Interface doc if protocols change
4. Update this index with new sections/cross-references
5. Increment date stamp in each modified document

### Known Limitations
- CMAC internal details are high-level (Xilinx IP)
- Some transceiver wizard IP details are abstracted
- Focus is on signal path, not full feature set
- Performance numbers are typical, not guaranteed

---

## Additional Resources

### External References
- IEEE 802.3-2018: Ethernet standards
- Xilinx UG576: UltraScale+ GTY Transceivers
- Xilinx UG583: UltraScale+ GTH Transceivers
- ARM IHI0024: AMBA AXI4-Stream Protocol
- Xilinx PG203: 100G Ethernet Subsystem (CMAC)

### Internal Code References
- `src/eth/rtl/`: Core Ethernet RTL modules
- `src/eth/rtl/us/`: UltraScale+-specific wrappers
- `src/eth/example/`: Board-specific top levels
- `src/xfcp/rtl/`: XFCP control protocol

---

## Questions & Support

For questions about:
- **Signal paths**: Reference the appropriate platform document
- **Specific interface**: Check CRITICAL_INTERFACES_AND_PROTOCOLS.md
- **Choosing configuration**: Read SIGNAL_PATH_DOCUMENTATION_SUMMARY.md
- **Module details**: Follow file paths in documents, then read source code

---

**Document Index Version**: 1.0  
**Last Updated**: 2026-09-12  
**Total Documentation**: 5 documents, ~70 KB
