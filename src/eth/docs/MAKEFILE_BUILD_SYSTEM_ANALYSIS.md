# Makefile-Based FPGA Build System Analysis

This document analyzes the Makefile-based build system used in the Taxi Ethernet FPGA projects, using the ZCU106 10G example as a reference.

## Build System Overview

The build system uses a **two-tier Makefile structure**:
1. **Project-specific Makefile** (`fpga_10g/Makefile`) - defines sources and configuration
2. **Common build infrastructure** (`common/vivado.mk`) - implements build rules

This approach provides:
- **Reusability**: Common build logic shared across all designs
- **Simplicity**: Projects only specify sources and settings
- **Consistency**: All designs build the same way
- **Automation**: Complete flow from sources to bitstream

### Vivado Project Mode

**Important**: This build system uses **Vivado Project Mode**, which creates a project file (`.xpr`) and managed directories (`*.cache`, `*.gen`, `*.runs`, etc.). While project mode is used, the build is fully automated via Makefile and batch-mode TCL scripts.

**Key characteristics**:
- ✓ Project file (`fpga.xpr`) managed by build system
- ✓ GUI debugging available via `make vivado`
- ✓ Automatic IP core management
- ✓ Project regenerated from sources (throwaway)
- ✓ Only sources tracked in version control

**For detailed explanation of Project Mode vs Non-Project Mode**, see: [VIVADO_PROJECT_MODE_EXPLAINED.md](VIVADO_PROJECT_MODE_EXPLAINED.md)

---

## File Structure

```
src/eth/example/ZCU106/fpga/
├── fpga_10g/                          # Build directory
│   ├── Makefile                       # Project-specific settings
│   └── config.tcl                     # Vivado parameter overrides
├── rtl/                               # RTL source files
│   ├── fpga.sv                        # Top-level
│   └── fpga_core.sv                   # Core logic
├── syn/                               # Synthesis constraints
│   ├── fpga.xdc                       # General constraints
│   ├── gpio.xdc                       # GPIO pin assignments
│   └── sfp.xdc                        # SFP+ constraints
├── common/
│   └── vivado.mk                      # Common build rules
└── lib/
    └── taxi/                          # Taxi framework library
        └── src/
            ├── eth/rtl/               # Ethernet modules
            ├── xfcp/rtl/              # Control protocol
            ├── axis/rtl/              # AXI-Stream modules
            └── sync/rtl/              # Synchronization modules
```

---

## Project-Specific Makefile Analysis

**Location**: `src/eth/example/ZCU106/fpga/fpga_10g/Makefile`

### 1. FPGA Configuration
```makefile
# FPGA settings
FPGA_PART = xczu7ev-ffvc1156-2-e     # Zynq UltraScale+ part number
FPGA_TOP = fpga                       # Top-level module name
FPGA_ARCH = zynquplus                 # Architecture (for reference)
```

**Purpose**: Defines the target FPGA device and design hierarchy.

### 2. Path Configuration
```makefile
RTL_DIR = ../rtl                      # Local RTL files
LIB_DIR = ../lib                      # Library location
TAXI_SRC_DIR = $(LIB_DIR)/taxi/src   # Taxi framework source
```

**Purpose**: Establishes source tree navigation. All paths are relative to build directory.

### 3. Source File Lists
```makefile
# Files for synthesis
SYN_FILES = $(RTL_DIR)/fpga.sv
SYN_FILES += $(RTL_DIR)/fpga_core.sv
SYN_FILES += $(TAXI_SRC_DIR)/eth/rtl/us/taxi_eth_mac_25g_us.f
SYN_FILES += $(TAXI_SRC_DIR)/xfcp/rtl/taxi_xfcp_if_uart.f
SYN_FILES += $(TAXI_SRC_DIR)/xfcp/rtl/taxi_xfcp_switch.sv
...
```

**File List Files (.f)**:
- Files ending in `.f` are **file list files**
- They contain additional source files, one per line
- Paths are relative to the `.f` file location
- Processed recursively with automatic de-duplication

**Example** (`taxi_eth_mac_25g_us.f`):
```
taxi_eth_mac_25g_us.sv              # In same directory
taxi_eth_mac_25g_us_ch.sv
taxi_eth_phy_25g_us_gt.f            # Another .f file (recursive)
../taxi_eth_mac_phy_10g.f           # Relative path to parent dir
../../lib/taxi/src/apb/rtl/taxi_apb_interconnect_1s.sv
```

### 4. Constraint Files (XDC)
```makefile
# XDC files
XDC_FILES += ../syn/fpga.xdc         # General constraints
XDC_FILES += ../syn/gpio.xdc         # GPIO pins
XDC_FILES += ../syn/sfp.xdc          # SFP+ transceivers
XDC_FILES += $(TAXI_SRC_DIR)/eth/syn/vivado/taxi_eth_mac_fifo.tcl
XDC_FILES += $(TAXI_SRC_DIR)/axis/syn/vivado/taxi_axis_async_fifo.tcl
XDC_FILES += $(TAXI_SRC_DIR)/sync/syn/vivado/taxi_sync_reset.tcl
```

**Two types**:
- **XDC files** (`.xdc`): Standard Xilinx Design Constraints
- **TCL files** (`.tcl`): Scripted constraints (for parameterized modules)

### 5. IP Generation
```makefile
# IP
IP_TCL_FILES = $(TAXI_SRC_DIR)/eth/rtl/us/taxi_eth_phy_10g_us_gth_156.tcl
```

**Purpose**: TCL scripts that create Xilinx IP cores (e.g., GTH Transceiver Wizard).

### 6. Configuration Override
```makefile
# Configuration
CONFIG_TCL_FILES = ./config.tcl
```

**Purpose**: Project-specific parameter overrides applied to top-level module.

### 7. Include Common Rules
```makefile
include ../common/vivado.mk
```

**Purpose**: Imports all build targets and rules from common infrastructure.

### 8. Custom Programming Target
```makefile
program: $(FPGA_TOP).bit
	echo "open_hw_manager" > program.tcl
	echo "connect_hw_server" >> program.tcl
	echo "open_hw_target" >> program.tcl
	echo "current_hw_device [lindex [get_hw_devices] 0]" >> program.tcl
	echo "refresh_hw_device -update_hw_probes false [current_hw_device]" >> program.tcl
	echo "set_property PROGRAM.FILE {$(FPGA_TOP).bit} [current_hw_device]" >> program.tcl
	echo "program_hw_devices [current_hw_device]" >> program.tcl
	echo "exit" >> program.tcl
	vivado -nojournal -nolog -mode batch -source program.tcl
```

**Purpose**: Generates TCL script and programs FPGA via JTAG.

---

## Configuration TCL File Analysis

**Location**: `fpga_10g/config.tcl`

```tcl
set params [dict create]

# MAC configuration
dict set params CFG_LOW_LATENCY "1"    # Enable low latency mode
dict set params COMBINED_MAC_PCS "1"   # Integrate MAC+PCS
dict set params MAC_DATA_W "32"        # 32-bit datapath (10G)

# apply parameters to top-level
set param_list {}
dict for {name value} $params {
    lappend param_list $name=$value
}

set_property generic $param_list [get_filesets sources_1]
```

**Purpose**: 
- Overrides SystemVerilog parameters on the top-level module
- Applied during project creation and synthesis
- Allows same RTL to support multiple configurations (10G vs 100G)

**Effect**:
```systemverilog
// Top-level module with these parameters overridden
module fpga #(
    parameter MAC_DATA_W = 32,           // Set by config.tcl
    parameter CFG_LOW_LATENCY = 1'b1,    // Set by config.tcl
    parameter COMBINED_MAC_PCS = 1'b1    // Set by config.tcl
)
```

---

## Common Build Infrastructure Analysis

**Location**: `common/vivado.mk`

### Build Flow Overview

```
make all/fpga
    ↓
$(PROJECT).bit (target)
    ↓
└─ Requires: $(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp
          ↓
          └─ Requires: $(PROJECT).runs/synth_1/$(PROJECT).dcp
                ↓
                └─ Requires: $(PROJECT).xpr
                      ↓
                      └─ Requires: create_project.tcl, update_config.tcl
```

### Key Features

#### 1. File List Processing
```makefile
# Recursive .f file processing
process_f_file = $(call process_f_files,$(addprefix $(dir $1),$(shell cat $1)))
process_f_files = $(foreach f,$1,$(if $(filter %.f,$f),$(call process_f_file,$f),$f))

# De-duplication (last occurrence wins)
uniq_base = $(if $1,$(call uniq_base,$(foreach f,$1,$(if $(filter-out $(notdir $(lastword $1)),$(notdir $f)),$f,))) $(lastword $1))

SYN_FILES := $(call uniq_base,$(call process_f_files,$(SYN_FILES)))
```

**How it works**:
1. Reads each `.f` file
2. Resolves paths relative to `.f` file location
3. Recursively processes nested `.f` files
4. De-duplicates based on filename (keeps last occurrence)

#### 2. Define Handling
```makefile
create_project.tcl: Makefile $(XCI_FILES) $(IP_TCL_FILES)
	rm -rf defines.v
	touch defines.v
	for x in $(DEFS); do echo '`define' $$x >> defines.v; done
```

**Purpose**: Converts Makefile defines into Verilog `define` statements.

**Usage**:
```makefile
DEFS = SIMULATION DEBUG_ENABLED
# Creates defines.v with:
# `define SIMULATION
# `define DEBUG_ENABLED
```

### Build Stages

#### Stage 1: Project Creation
```makefile
create_project.tcl: Makefile $(XCI_FILES) $(IP_TCL_FILES)
	echo "create_project -force -part $(FPGA_PART) $(PROJECT)" > $@
	echo "add_files -fileset sources_1 defines.v $(SYN_FILES)" >> $@
	echo "set_property top $(FPGA_TOP) [current_fileset]" >> $@
	echo "add_files -fileset constrs_1 $(XDC_FILES)" >> $@
	for x in $(XCI_FILES); do echo "import_ip $$x" >> $@; done
	for x in $(IP_TCL_FILES); do echo "source $$x" >> $@; done
	for x in $(CONFIG_TCL_FILES); do echo "source $$x" >> $@; done
```

**Triggers**: 
- Makefile changes
- IP files change
- New IP TCL scripts

**Creates**: TCL script that:
1. Creates Vivado project
2. Adds all source files
3. Sets top-level module
4. Adds constraints
5. Imports/creates IP cores
6. Applies configuration

#### Stage 2: Configuration Update
```makefile
update_config.tcl: $(CONFIG_TCL_FILES) $(SYN_FILES) $(INC_FILES) $(XDC_FILES)
	echo "open_project -quiet $(PROJECT).xpr" > $@
	for x in $(CONFIG_TCL_FILES); do echo "source $$x" >> $@; done
```

**Triggers**: 
- Configuration TCL changes
- Any source file changes
- Constraint file changes

**Purpose**: Re-applies configuration when sources change without recreating project.

#### Stage 3: Project File Generation
```makefile
$(PROJECT).xpr: create_project.tcl update_config.tcl
	vivado -nojournal -nolog -mode batch $(foreach x,$?,-source $x)
```

**Executes**: Any changed TCL scripts in batch mode to create/update `.xpr` file.

#### Stage 4: Synthesis
```makefile
$(PROJECT).runs/synth_1/$(PROJECT).dcp: create_project.tcl update_config.tcl \
                                         $(SYN_FILES) $(INC_FILES) $(XDC_FILES) \
                                         | $(PROJECT).xpr
	echo "open_project $(PROJECT).xpr" > run_synth.tcl
	echo "reset_run synth_1" >> run_synth.tcl
	echo "launch_runs -jobs 4 synth_1" >> run_synth.tcl
	echo "wait_on_run synth_1" >> run_synth.tcl
	vivado -nojournal -nolog -mode batch -source run_synth.tcl
```

**Triggers**:
- Source file changes
- Configuration changes
- Constraint changes

**Output**: Synthesized design checkpoint (`.dcp`)

**Parallelism**: `-jobs 4` uses 4 parallel synthesis threads

#### Stage 5: Implementation
```makefile
$(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp: \
    $(PROJECT).runs/synth_1/$(PROJECT).dcp
	echo "open_project $(PROJECT).xpr" > run_impl.tcl
	echo "reset_run impl_1" >> run_impl.tcl
	echo "launch_runs -jobs 4 impl_1" >> run_impl.tcl
	echo "wait_on_run impl_1" >> run_impl.tcl
	echo "open_run impl_1" >> run_impl.tcl
	echo "report_utilization -file $(PROJECT)_utilization.rpt" >> run_impl.tcl
	echo "report_utilization -hierarchical -file $(PROJECT)_utilization_hierarchical.rpt" >> run_impl.tcl
	vivado -nojournal -nolog -mode batch -source run_impl.tcl
```

**Stages**:
1. **Opt Design**: Optimization
2. **Place Design**: Component placement
3. **Route Design**: Interconnect routing
4. **Report Generation**: Utilization reports

**Output**: Routed design checkpoint (`.dcp`)

#### Stage 6: Bitstream Generation
```makefile
$(PROJECT).bit $(PROJECT).bin $(PROJECT).ltx $(PROJECT).xsa: \
    $(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp
	echo "open_project $(PROJECT).xpr" > generate_bit.tcl
	echo "open_run impl_1" >> generate_bit.tcl
	echo "write_bitstream -force -bin_file $(PROJECT).runs/impl_1/$(PROJECT).bit" >> generate_bit.tcl
	echo "write_debug_probes -force $(PROJECT).runs/impl_1/$(PROJECT).ltx" >> generate_bit.tcl
	echo "write_hw_platform -fixed -force -include_bit $(PROJECT).xsa" >> generate_bit.tcl
	vivado -nojournal -nolog -mode batch -source generate_bit.tcl
	ln -f -s $(PROJECT).runs/impl_1/$(PROJECT).bit .
	ln -f -s $(PROJECT).runs/impl_1/$(PROJECT).bin .
	if [ -e $(PROJECT).runs/impl_1/$(PROJECT).ltx ]; then \
	    ln -f -s $(PROJECT).runs/impl_1/$(PROJECT).ltx .; fi
	# Archive to rev/ directory with incrementing revision numbers
	mkdir -p rev
	COUNT=100; \
	while [ -e rev/$(PROJECT)_rev$$COUNT.bit ]; \
	do COUNT=$$((COUNT+1)); done; \
	cp -pv $(PROJECT).runs/impl_1/$(PROJECT).bit rev/$(PROJECT)_rev$$COUNT.bit
	...
```

**Output Files**:
- **`.bit`**: FPGA bitstream file (for programming)
- **`.bin`**: Binary format (for flash programming)
- **`.ltx`**: Logic analyzer probes (for ILA debugging)
- **`.xsa`**: Hardware platform (for Vitis/PetaLinux)

**Archiving**: Automatically creates `rev/` directory with numbered revisions (rev100, rev101, ...)

### Make Targets

```makefile
.PHONY: fpga vivado tmpclean clean distclean

all: fpga                  # Default target: build bitstream

fpga: $(PROJECT).bit       # Build complete bitstream

vivado: $(PROJECT).xpr     # Open project in Vivado GUI
	vivado $(PROJECT).xpr

tmpclean::                 # Remove intermediate build files
	-rm -rf *.log *.jou *.cache *.gen *.hw *.runs *.xpr ...

clean:: tmpclean           # Remove output files
	-rm -rf *.bit *.bin *.ltx *.xsa program.tcl ...

distclean:: clean          # Remove archived revisions
	-rm -rf rev
```

**Usage**:
```bash
make              # Build bitstream
make vivado       # Open in GUI
make clean        # Clean build artifacts
make fpga         # Explicit bitstream target
make program      # Program FPGA (project-specific)
```

---

## IP Generation: GTH Transceiver Example

**Location**: `src/eth/rtl/us/taxi_eth_phy_10g_us_gth_156.tcl`

### TCL Script Analysis

```tcl
# Configuration
set base_name {taxi_eth_phy_10g_us_gth}
set preset {GTH-10GBASE-R}
set line_rate {10.3125}              # Gbps
set refclk_freq {156.25}             # MHz
set user_data_width {32}             # bits

# GT Wizard configuration dictionary
set config [dict create]
dict set config TX_LINE_RATE $line_rate
dict set config TX_REFCLK_FREQUENCY $refclk_freq
dict set config TX_USER_DATA_WIDTH $user_data_width
dict set config RX_LINE_RATE $line_rate
...

# IP creation procedure
proc create_gtwizard_ip {name preset config} {
    create_ip -name gtwizard_ultrascale \
              -vendor xilinx.com \
              -library ip \
              -module_name $name
    set ip [get_ips $name]
    set_property CONFIG.preset $preset $ip
    # Apply all configuration
    set config_list {}
    dict for {name value} $config {
        lappend config_list "CONFIG.${name}" $value
    }
    set_property -dict $config_list $ip
}

# Generate normal and low-latency variants
create_gtwizard_ip ${base_name} $preset $config
create_gtwizard_ip ${base_name}_ll $preset $config_ll
```

**Generated IP**:
- `taxi_eth_phy_10g_us_gth`: Standard latency GTH wrapper
- `taxi_eth_phy_10g_us_gth_ll`: Low-latency variant

**Customization**:
- Line rate: 10.3125 Gbps
- Reference clock: 156.25 MHz
- User data width: 32-bit
- Encoding: 64B/66B
- Extra ports for DRP, reset control, EQ settings

---

## Constraint Files (XDC)

### General Constraints

**Location**: `syn/fpga.xdc`

```tcl
# Bitstream compression
set_property BITSTREAM.GENERAL.COMPRESS true [current_design]

# System clocks
set_property -dict {LOC H9 IOSTANDARD LVDS} [get_ports clk_125mhz_p]
set_property -dict {LOC G9 IOSTANDARD LVDS} [get_ports clk_125mhz_n]
create_clock -period 8.000 -name clk_125mhz [get_ports clk_125mhz_p]
```

### GPIO Constraints

**Location**: `syn/gpio.xdc`

```tcl
# Push buttons (active low)
set_property -dict {LOC A17  IOSTANDARD LVCMOS33} [get_ports btnc]
set_property -dict {LOC A16  IOSTANDARD LVCMOS33} [get_ports btnd]
...

# LEDs
set_property -dict {LOC AL11 IOSTANDARD LVCMOS33 SLEW SLOW DRIVE 8} [get_ports {led[0]}]
...
```

### SFP+ Constraints

**Location**: `syn/sfp.xdc`

```tcl
# SFP+ reference clock (156.25 MHz)
set_property -dict {LOC G8} [get_ports sfp_mgt_refclk_0_p]
set_property -dict {LOC G7} [get_ports sfp_mgt_refclk_0_n]
create_clock -period 6.400 -name sfp_mgt_refclk_0 [get_ports sfp_mgt_refclk_0_p]

# SFP+ TX/RX differential pairs (GTH locations)
set_property -dict {LOC W4} [get_ports {sfp_tx_p[0]}]
set_property -dict {LOC W3} [get_ports {sfp_tx_n[0]}]
set_property -dict {LOC Y2} [get_ports {sfp_rx_p[0]}]
set_property -dict {LOC Y1} [get_ports {sfp_rx_n[0]}]
...
```

### TCL-based Constraints

**Example**: `taxi_axis_async_fifo.tcl`

```tcl
# Automatically constrain asynchronous FIFOs
foreach inst [get_cells -hier -filter {(ORIG_REF_NAME == taxi_axis_async_fifo || \
    REF_NAME == taxi_axis_async_fifo)}] {
    puts "Inserting timing constraints for taxi_axis_async_fifo instance $inst"
    
    # Constrain gray code synchronizers
    set_bus_skew -from [get_cells "$inst/wr_ptr_gray_reg[*]"] \
                 -to [get_cells "$inst/wr_ptr_gray_sync_reg[*]"] 0.1
    
    set_max_delay -from [get_cells "$inst/wr_ptr_gray_reg[*]"] \
                  -to [get_cells "$inst/wr_ptr_gray_sync_reg[*]"] 8.0 -datapath_only
    ...
}
```

**Purpose**: Automatically applies timing constraints to parameterized modules.

---

## Build Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ User Input                                                    │
├──────────────────────────────────────────────────────────────┤
│ • Makefile (sources, constraints)                            │
│ • config.tcl (parameter overrides)                           │
│ • RTL source files (.sv, .v)                                 │
│ • Constraint files (.xdc, .tcl)                              │
│ • IP generation scripts (.tcl)                               │
└────────────────────┬─────────────────────────────────────────┘
                     ↓
         ┌───────────────────────┐
         │ File List Processing  │  ← Recursive .f file expansion
         │ (.f files)            │  ← De-duplication
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ create_project.tcl    │  ← Generate project creation script
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ update_config.tcl     │  ← Apply config.tcl parameters
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Vivado Project (.xpr) │  ← Execute TCL scripts
         │ • Import sources      │
         │ • Generate IP cores   │
         │ • Apply constraints   │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ run_synth.tcl         │  ← Generate synthesis script
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Synthesis             │  ← Vivado batch mode (-jobs 4)
         │ • Elaborate design    │
         │ • Synthesize logic    │
         │ • Create netlist      │
         └───────────┬───────────┘
                     ↓
         $(PROJECT).runs/synth_1/$(PROJECT).dcp
                     ↓
         ┌───────────────────────┐
         │ run_impl.tcl          │  ← Generate implementation script
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Implementation        │  ← Vivado batch mode (-jobs 4)
         │ • Optimize design     │
         │ • Place components    │
         │ • Route interconnect  │
         │ • Generate reports    │
         └───────────┬───────────┘
                     ↓
         $(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp
                     ↓
         ┌───────────────────────┐
         │ generate_bit.tcl      │  ← Generate bitstream script
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Bitstream Generation  │  ← Vivado batch mode
         │ • Write bitstream     │
         │ • Write debug probes  │
         │ • Create .xsa file    │
         └───────────┬───────────┘
                     ↓
┌──────────────────────────────────────────────────────────────┐
│ Output Files                                                  │
├──────────────────────────────────────────────────────────────┤
│ • fpga.bit       - FPGA bitstream                            │
│ • fpga.bin       - Binary format                             │
│ • fpga.ltx       - Debug probe file                          │
│ • fpga.xsa       - Hardware platform export                  │
│ • fpga_utilization.rpt - Resource usage                      │
│ • rev/fpga_revXXX.* - Archived revisions                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Features and Benefits

### 1. Incremental Builds
- **Smart dependency tracking**: Only rebuilds when sources change
- **Checkpoint-based**: Reuses synthesis if only constraints changed
- **Fast iteration**: Constraint-only changes skip synthesis (minutes vs hours)

### 2. Parameterization
- **config.tcl**: Same RTL supports multiple configurations
- **Example**: 10G vs 100G via `MAC_DATA_W` parameter
- **No code duplication**: Single source base for all variants

### 3. Modularity
- **File list files**: Hierarchical source organization
- **Automatic inclusion**: Modules bring their dependencies
- **No manual management**: Add one .f file, get entire module tree

### 4. Reproducibility
- **Versioned builds**: Automatic revision numbering
- **Archived outputs**: Every build saved in `rev/` directory
- **Traceable**: Build logs and reports included

### 5. Automation
- **No GUI required**: Complete builds via command line
- **CI/CD friendly**: Scriptable, batch-mode execution
- **Parallel builds**: Multi-threaded synthesis and implementation

---

## Build Time Estimates

| Stage | Typical Time | Notes |
|-------|-------------|-------|
| File list processing | <1 sec | Pure Make logic |
| Project creation | 5-10 sec | One-time or after IP changes |
| IP generation | 1-5 min | GTH wizard, first time only |
| Synthesis | 5-20 min | Depends on design size |
| Implementation | 10-40 min | Place and route |
| Bitstream generation | 1-2 min | Final output |
| **Total (clean build)** | **20-70 min** | XCZU7EV, ~20K LUTs |
| **Incremental (XDC only)** | **10-40 min** | Skip synthesis |

---

## Usage Examples

### Basic Build
```bash
cd src/eth/example/ZCU106/fpga/fpga_10g
make              # Build bitstream
# Output: fpga.bit, fpga.bin, fpga.ltx
```

### Open in Vivado GUI
```bash
make vivado       # Opens fpga.xpr
# Useful for manual inspection, debugging
```

### Clean and Rebuild
```bash
make clean        # Remove outputs and project
make              # Full rebuild from scratch
```

### Program FPGA
```bash
make program      # Program via JTAG
# Requires hardware connected and powered
```

### Configuration Change
```bash
# Edit config.tcl to change MAC_DATA_W
vim config.tcl    # Change MAC_DATA_W from 32 to 64
make              # Automatic rebuild with new parameters
```

### Parallel Builds (Multiple Configurations)
```bash
# Terminal 1: 10G build
cd fpga_10g && make

# Terminal 2: 1G build (if exists)
cd fpga_1g && make

# Builds run independently in separate directories
```

---

## Advanced Features

### Custom IP Integration

Add to Makefile:
```makefile
XCI_FILES = ip/custom_ip.xci      # Pre-generated IP
# OR
IP_TCL_FILES = scripts/gen_custom_ip.tcl  # Script to generate IP
```

### Multiple Configurations

Create multiple build directories:
```
fpga/
├── fpga_10g/          # 10G configuration
│   ├── Makefile → shares ../rtl/
│   └── config.tcl → MAC_DATA_W=32
├── fpga_100g/         # 100G configuration
│   ├── Makefile → shares ../rtl/
│   └── config.tcl → MAC_DATA_W=512
└── rtl/               # Shared RTL source
    ├── fpga.sv
    └── fpga_core.sv
```

### Conditional Compilation

Add to Makefile:
```makefile
DEFS = SIMULATION DEBUG_ETHERNET

# In RTL:
`ifdef SIMULATION
    // Simulation-only code
`endif
```

### Custom Build Scripts

Override stages:
```makefile
# In project Makefile, after include vivado.mk
$(PROJECT).runs/synth_1/$(PROJECT).dcp: ...
	# Custom synthesis script
	vivado -mode batch -source my_custom_synth.tcl
```

---

## Troubleshooting

### Build Fails During File List Processing
**Symptom**: Make errors about missing files
**Cause**: Broken path in .f file
**Fix**: Check relative paths in .f files are correct

### IP Generation Fails
**Symptom**: TCL script errors during create_project.tcl
**Cause**: Incompatible Vivado version, missing IP license
**Fix**: Check Vivado version, verify IP is available

### Synthesis Fails
**Symptom**: Errors in synthesis stage
**Fix**: 
```bash
make clean       # Clear cached state
make vivado      # Open GUI to debug
# Review error messages in Vivado GUI
```

### Out-of-Date Dependencies
**Symptom**: Changes not picked up by Make
**Fix**:
```bash
make clean       # Force full rebuild
make
# Or touch files to update timestamps
touch ../rtl/fpga.sv
make
```

---

## Comparison with Other Build Systems

| Feature | Makefile | Vivado TCL | Vivado GUI |
|---------|----------|------------|------------|
| Automation | ✓✓✓ | ✓✓ | ✗ |
| Reproducibility | ✓✓✓ | ✓✓ | ✗ |
| CI/CD | ✓✓✓ | ✓✓ | ✗ |
| Learning Curve | Medium | Low | Low |
| Flexibility | ✓✓✓ | ✓✓✓ | ✓ |
| Version Control | ✓✓✓ (Makefile) | ✓✓✓ (TCL) | ✗ |
| Parallel Builds | ✓✓✓ | ✓ | ✗ |

---

## Best Practices

### 1. Directory Organization
- **Keep build dirs separate**: `fpga_10g/`, `fpga_100g/`
- **Share RTL sources**: Single `rtl/` directory
- **Version control**: Add `*.bit`, `*.xpr`, `*.runs` to `.gitignore`

### 2. Source Management
- **Use .f files**: Modular source organization
- **Relative paths**: All paths relative to .f file location
- **De-duplication**: Let Make handle duplicate includes

### 3. Configuration
- **Use config.tcl**: Parameterize designs, avoid RTL duplication
- **Document parameters**: Comment what each parameter does
- **Test variants**: Build all configurations regularly

### 4. Build Hygiene
- **Clean periodically**: `make clean` before releases
- **Archive revisions**: Keep `rev/` directory with releases
- **Check reports**: Review utilization, timing after builds

### 5. Version Control
```bash
# .gitignore
*.bit
*.bin
*.ltx
*.xpr
*.runs
*.cache
*.hw
*.ip_user_files
defines.v
*.tcl  # Generated TCL scripts
```

---

## Summary

The Makefile-based build system provides:

✓ **Automated** - Complete builds with single command  
✓ **Reproducible** - Consistent results across machines  
✓ **Modular** - Hierarchical source organization via .f files  
✓ **Parameterized** - Multiple configurations from same sources  
✓ **Incremental** - Smart rebuilds save time  
✓ **Portable** - Works on any system with Vivado and Make  
✓ **CI/CD Ready** - Batch-mode execution for automation  

This system successfully decouples project configuration from build mechanics, allowing designers to focus on RTL and parameters while the infrastructure handles the complex Vivado build flow.

---

**Document Version**: 1.0  
**Last Updated**: 2026-09-12  
**Example Project**: ZCU106 10G Ethernet  
**Build System**: vivado.mk v2025
