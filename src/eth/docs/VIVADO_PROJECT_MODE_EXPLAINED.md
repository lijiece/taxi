# Vivado Project Mode vs Non-Project Mode

**Yes, this build system uses Vivado Project Mode.** This document explains what that means, the implications, and the trade-offs.

---

## Quick Answer

The build system creates and manages a **Vivado Project** (`.xpr` file) with associated managed directories. This is called **Project Mode**.

### Evidence:
```bash
$ ls -la fpga_10g/
fpga.xpr                    # ← Project file (XML database)
fpga.cache/                 # ← IP cache
fpga.gen/                   # ← Generated files
fpga.hw/                    # ← Hardware manager
fpga.ip_user_files/         # ← IP user files
fpga.runs/                  # ← Synthesis/implementation runs
  ├── synth_1/              # ← Synthesis run
  └── impl_1/               # ← Implementation run
fpga.sim/                   # ← Simulation files
fpga.srcs/                  # ← Source management (filesets)
```

---

## Vivado Build Modes Comparison

Vivado supports two distinct build methodologies:

### 1. Project Mode (Used Here)
**Creates and manages** a project file (`.xpr`) and directory structure.

```tcl
# Evidence in vivado.mk (line 100):
echo "create_project -force -part $(FPGA_PART) $(PROJECT)" > $@

# Evidence (line 113):
$(PROJECT).xpr: create_project.tcl update_config.tcl
    vivado -nojournal -nolog -mode batch $(foreach x,$?,-source $x)
```

### 2. Non-Project Mode (Not Used)
**Pure TCL scripts** with no project file or managed directories.

```tcl
# Example non-project mode (NOT what this build system does):
read_verilog fpga.v
read_xdc fpga.xdc
synth_design -top fpga -part xczu7ev-ffvc1156-2-e
write_checkpoint synth.dcp
opt_design
place_design
route_design
write_bitstream fpga.bit
```

---

## Detailed Comparison

| Feature | Project Mode (This System) | Non-Project Mode |
|---------|---------------------------|------------------|
| **Project File** | Yes (`.xpr`) | No |
| **Managed Directories** | Yes (`*.runs`, `*.cache`, etc.) | No |
| **GUI Support** | Full | Limited |
| **File Organization** | Automatic (filesets) | Manual |
| **IP Management** | Automatic (IP Catalog) | Manual instantiation |
| **Build Runs** | Named runs (synth_1, impl_1) | Direct commands |
| **Incremental Builds** | Automatic | Manual scripting |
| **Disk Usage** | Higher (cached files) | Lower |
| **Version Control** | More files to ignore | Cleaner |
| **Debugging** | Easier (open in GUI) | Harder (recreate state) |
| **Portability** | Good (project + sources) | Better (just TCL) |
| **Automation** | Via TCL + GUI | Pure TCL |
| **Learning Curve** | Lower (GUI available) | Higher |

---

## Project Mode Directory Structure

### Top-Level Files
```bash
fpga.xpr                    # Vivado project file (XML)
├── Project settings
├── Source file references (not copies)
├── IP core configurations
├── Constraint file references
├── Run configurations
└── Tool settings
```

### Managed Directories

#### `fpga.cache/`
**Purpose**: IP cache for faster IP regeneration
```bash
fpga.cache/
├── ip/                     # IP output products cache
└── compile_simlib/         # Simulation library cache
```
**Size**: Can be 100s of MB  
**Regenerated**: Automatically by Vivado  
**Version Control**: Add to `.gitignore`

#### `fpga.gen/`
**Purpose**: Generated IP output products
```bash
fpga.gen/
└── sources_1/
    └── ip/
        ├── taxi_eth_phy_10g_us_gth/     # Generated GTH wizard
        │   ├── *.v, *.vhd               # Generated RTL
        │   ├── *.xci                    # IP configuration
        │   └── synth/                   # Synthesis files
        └── ...
```
**Size**: 10s to 100s of MB per IP  
**Regenerated**: When IP configuration changes  
**Version Control**: Add to `.gitignore` (regenerated from `.tcl`)

#### `fpga.hw/`
**Purpose**: Hardware manager data (programming, probes)
```bash
fpga.hw/
└── hw_1/                   # Hardware target
    ├── wave/               # ILA waveforms
    └── probes/             # Debug probe files
```
**Size**: Small (KB to MB)  
**Created**: When using hardware manager  
**Version Control**: Add to `.gitignore`

#### `fpga.ip_user_files/`
**Purpose**: User-modifiable IP files (simulation, constraints)
```bash
fpga.ip_user_files/
├── ip/                     # Per-IP user files
├── sim_scripts/            # Simulation TCL scripts
└── mem_init_files/         # Memory initialization files
```
**Size**: Usually small  
**Version Control**: Generally ignore, unless customized

#### `fpga.runs/`
**Purpose**: Synthesis and implementation run results
```bash
fpga.runs/
├── synth_1/                # Synthesis run
│   ├── fpga.dcp            # Post-synthesis checkpoint
│   ├── runme.log           # Run log
│   ├── *.rpt               # Reports
│   └── .vivado.begin.rst   # Run state
├── impl_1/                 # Implementation run  
│   ├── fpga.dcp            # Post-opt checkpoint
│   ├── fpga_routed.dcp     # Post-route checkpoint
│   ├── fpga.bit            # Bitstream
│   ├── fpga.bin            # Binary bitstream
│   ├── fpga.ltx            # Debug probes
│   ├── *.rpt               # Timing/utilization reports
│   └── .vivado.begin.rst   # Run state
└── .jobs/                  # Parallel job management
```
**Size**: 100s of MB to several GB  
**Critical**: Contains build outputs  
**Version Control**: **Add to `.gitignore`** (except archive to `rev/`)

#### `fpga.sim/`
**Purpose**: Simulation files and results
```bash
fpga.sim/
└── sim_1/
    └── behav/
        └── xsim/           # XSim simulation files
```
**Size**: Can be large (GB for long sims)  
**Version Control**: Add to `.gitignore`

#### `fpga.srcs/`
**Purpose**: Vivado's managed source organization
```bash
fpga.srcs/
├── sources_1/              # Design sources fileset
│   ├── new/                # Sources created in GUI
│   ├── ip/                 # IP core .xci files
│   └── imports/            # Imported sources (if copied)
├── constrs_1/              # Constraints fileset
│   └── new/
├── sim_1/                  # Simulation fileset
└── utils_1/                # Utilities
```
**Note**: By default, Vivado **references** external files, not copies  
**Version Control**: Usually add to `.gitignore` (sources tracked elsewhere)

---

## How This Build System Uses Project Mode

### 1. Project Creation
```makefile
# From vivado.mk line 96-106:
create_project.tcl: Makefile $(XCI_FILES) $(IP_TCL_FILES)
    echo "create_project -force -part $(FPGA_PART) $(PROJECT)" > $@
    echo "add_files -fileset sources_1 defines.v $(SYN_FILES)" >> $@
    echo "set_property top $(FPGA_TOP) [current_fileset]" >> $@
    echo "add_files -fileset constrs_1 $(XDC_FILES)" >> $@
    for x in $(IP_TCL_FILES); do echo "source $$x" >> $@; done
    for x in $(CONFIG_TCL_FILES); do echo "source $$x" >> $@; done
```

**Creates**:
- `fpga.xpr` project file
- References to source files (doesn't copy them)
- IP core instantiations via TCL scripts
- Fileset organization

### 2. Synthesis Run
```makefile
# From vivado.mk line 117-122:
$(PROJECT).runs/synth_1/$(PROJECT).dcp: ... | $(PROJECT).xpr
    echo "open_project $(PROJECT).xpr" > run_synth.tcl
    echo "reset_run synth_1" >> run_synth.tcl
    echo "launch_runs -jobs 4 synth_1" >> run_synth.tcl
    echo "wait_on_run synth_1" >> run_synth.tcl
    vivado -nojournal -nolog -mode batch -source run_synth.tcl
```

**Uses**:
- Opens existing project
- Launches **named run** `synth_1`
- Parallel execution (`-jobs 4`)
- Outputs to `fpga.runs/synth_1/`

### 3. Implementation Run
```makefile
# From vivado.mk line 125-133:
$(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp: ...
    echo "open_project $(PROJECT).xpr" > run_impl.tcl
    echo "reset_run impl_1" >> run_impl.tcl
    echo "launch_runs -jobs 4 impl_1" >> run_impl.tcl
    echo "wait_on_run impl_1" >> run_impl.tcl
    vivado -nojournal -nolog -mode batch -source run_impl.tcl
```

**Uses**:
- Opens project
- Launches **named run** `impl_1`
- Outputs to `fpga.runs/impl_1/`

### 4. GUI Access
```makefile
vivado: $(PROJECT).xpr
    vivado $(PROJECT).xpr
```

**Benefit**: Can open project in GUI for debugging
```bash
make vivado
# Opens Vivado GUI with full project context:
# - All sources
# - All IP cores
# - All runs and results
# - All reports
```

---

## Advantages of Project Mode (Why This System Uses It)

### 1. **GUI Debugging**
When a build fails, you can open the project in the GUI:
```bash
make vivado
```
- Inspect synthesized design
- View timing reports
- Analyze critical paths
- Check schematic
- Re-run with different options

### 2. **Automatic IP Management**
IP cores are managed by Vivado:
```tcl
# In IP_TCL_FILES (taxi_eth_phy_10g_us_gth_156.tcl):
create_ip -name gtwizard_ultrascale ...
```
- Auto-generates IP output products
- Handles dependencies
- Manages versions
- Caches for reuse

### 3. **Incremental Builds**
Vivado tracks what changed:
- Only re-synthesize if sources changed
- Reuse IP if configuration unchanged
- Smart checkpoint management

### 4. **Named Runs**
Clear organization:
```bash
fpga.runs/
├── synth_1/      # "This is the synthesis run"
└── impl_1/       # "This is the implementation run"
```
- Can create multiple implementation strategies
- Compare different optimization approaches
- Archive specific runs

### 5. **Filesets**
Logical source organization:
- `sources_1`: Design sources
- `constrs_1`: Constraints
- `sim_1`: Simulation sources
- Separate concerns

### 6. **Lower Learning Curve**
- Most Vivado documentation assumes project mode
- Examples and tutorials use project mode
- Familiar to engineers who used Vivado GUI

---

## Disadvantages of Project Mode

### 1. **Disk Space**
Large managed directories:
```bash
$ du -sh fpga.*
150M    fpga.cache
450M    fpga.gen
2.1G    fpga.runs
15M     fpga.ip_user_files
...
Total: ~2.7 GB for one build
```

### 2. **Version Control Complexity**
Many files to ignore:
```gitignore
*.xpr
*.cache
*.gen
*.hw
*.ip_user_files
*.runs
*.sim
*.srcs
```

### 3. **Hidden Logic**
Project manages things automatically:
- Where are IP sources?
- What exactly is being compiled?
- Less transparent than pure TCL

### 4. **Portability**
Project file contains:
- Absolute paths (sometimes)
- Machine-specific settings
- IP catalog cache locations

**Mitigation**: This build system regenerates project from sources

---

## Why Not Non-Project Mode?

### Comparison for This Use Case

**Non-Project Mode Would Require**:
```tcl
# Hypothetical non-project version:
read_verilog [glob ../rtl/*.sv]
read_verilog [glob ../lib/taxi/src/eth/rtl/*.sv]
# ... dozens more read_verilog commands ...

# Manual IP generation
source ../lib/taxi/src/eth/rtl/us/taxi_eth_phy_10g_us_gth_156.tcl
# ... wait for IP to generate ...

read_xdc ../syn/fpga.xdc
read_xdc ../syn/gpio.xdc
read_xdc ../syn/sfp.xdc

synth_design -top fpga -part xczu7ev-ffvc1156-2-e
write_checkpoint post_synth.dcp

opt_design
place_design  
route_design
write_checkpoint post_route.dcp

report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt

write_bitstream -force fpga.bit
```

**Issues**:
1. **No incremental builds**: Always from scratch
2. **Manual IP management**: Track dependencies yourself
3. **No GUI debugging**: Can't easily inspect intermediate results
4. **Complex scripting**: Must handle all error cases
5. **Less maintainable**: Harder to understand and modify

**Benefits**:
1. Cleaner (no managed directories)
2. More explicit (see every command)
3. Potentially faster (no overhead)
4. Better for CI/CD (simpler)

---

## Best of Both Worlds: This Build System

The build system gets benefits of both:

### Project Mode Advantages ✓
- GUI debugging available (`make vivado`)
- Automatic IP management
- Named runs and organization

### Non-Project Mode Advantages ✓
- **Automated**: Makefile-driven, no manual steps
- **Reproducible**: Regenerates project from sources
- **Scriptable**: Batch mode, no GUI required
- **Version control**: Only track sources and Makefile

### How?
1. **Project is generated**, not hand-crafted
2. **Sources referenced**, not copied into project
3. **Project is throwaway**: `make clean` removes it
4. **Real sources** tracked in version control
5. **Batch mode**: All builds via TCL scripts

---

## Practical Implications

### What to Version Control

**DO track**:
```bash
Makefile                    # Build configuration
config.tcl                  # Parameter overrides
../rtl/*.sv                 # Source files
../syn/*.xdc                # Constraints
```

**DON'T track** (add to `.gitignore`):
```bash
*.xpr                       # Project file (regenerated)
*.cache/                    # IP cache
*.gen/                      # Generated files
*.hw/                       # Hardware manager
*.ip_user_files/            # IP files
*.runs/                     # Build outputs
*.sim/                      # Simulation
*.srcs/                     # Source management
*.log, *.jou               # Vivado logs
defines.v                   # Generated defines
create_project.tcl          # Generated scripts
update_config.tcl
run_synth.tcl
run_impl.tcl
generate_bit.tcl
```

**DO track** (exceptions):
```bash
rev/                        # Archived bitstreams (optional)
*.bit, *.bin (in rev/)      # Released builds
```

### Cleaning Up

```bash
make tmpclean   # Remove intermediate files, keep outputs
                # Removes: *.xpr, *.cache, *.gen, *.runs, etc.

make clean      # Remove outputs too
                # Removes: *.bit, *.bin, *.ltx

make distclean  # Remove archived builds
                # Removes: rev/
```

### Disk Space Management

**During development**:
```bash
# Clean project between major changes
make clean && make

# Disk space used: ~3-5 GB per build directory
```

**Multiple configurations**:
```bash
fpga/
├── fpga_10g/    # ~3 GB
├── fpga_25g/    # ~3 GB  
└── fpga_100g/   # ~4 GB
Total: ~10 GB
```

**Tip**: Use separate disk or partition for build outputs

---

## When Each Mode Makes Sense

### Use Project Mode (Like This System) When:
- ✓ Team uses Vivado GUI for debugging
- ✓ Design uses Xilinx IP cores
- ✓ Want incremental build support
- ✓ Disk space not constrained
- ✓ Build time more important than disk space

### Use Non-Project Mode When:
- ✓ Pure TCL automation preferred
- ✓ Minimal disk usage required
- ✓ No IP cores (or manual instantiation OK)
- ✓ Complete build control needed
- ✓ CI/CD in constrained environments

### This System's Choice: ✓ Project Mode
**Why**: Gets project mode benefits while automating away the downsides through Makefile regeneration and batch-mode builds.

---

## Project Mode Commands Reference

### Project Creation
```tcl
create_project -force -part xczu7ev-ffvc1156-2-e fpga
```

### Project Manipulation
```tcl
open_project fpga.xpr
close_project
save_project_as new_fpga.xpr
```

### Adding Files
```tcl
add_files -fileset sources_1 rtl/fpga.sv
add_files -fileset constrs_1 syn/fpga.xdc
import_files -force -norecurse  # Copy into project
```

### Run Management
```tcl
launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -to_step route_design
reset_run impl_1
delete_runs old_run_1
```

### Checkpoints
```tcl
open_run synth_1
open_checkpoint fpga.runs/impl_1/fpga_routed.dcp
write_checkpoint my_checkpoint.dcp
```

---

## Migration to Non-Project Mode

If you wanted to convert to non-project mode, you would:

1. **Replace** `create_project.tcl` with direct commands:
```tcl
# Instead of:
create_project ...
add_files ...

# Do:
read_verilog fpga.sv
read_verilog fpga_core.sv
# ... all sources ...
```

2. **Replace** `launch_runs` with direct commands:
```tcl
# Instead of:
launch_runs synth_1

# Do:
synth_design -top fpga -part xczu7ev-ffvc1156-2-e
```

3. **Manual IP management**:
```tcl
# Still need IP wizard, but:
# - Generate once
# - Check in output products
# - Or regenerate each build
```

4. **Remove** `.xpr` and managed directories

5. **Direct output** to specific files:
```tcl
write_bitstream -force output/fpga.bit
```

**Effort**: Moderate (few days)  
**Benefit**: Cleaner, more explicit  
**Cost**: Lose GUI debugging, incremental builds

---

## Summary

### Project Mode Characteristics (This System)

| Aspect | Status |
|--------|--------|
| **Mode** | Project Mode |
| **Project File** | `fpga.xpr` |
| **Managed Dirs** | Yes (9 directories) |
| **Automation** | Full (Makefile + batch TCL) |
| **GUI Access** | Yes (`make vivado`) |
| **Incremental** | Yes (Vivado managed) |
| **Disk Usage** | ~3-5 GB per build |
| **Version Control** | Sources only (project regenerated) |
| **Learning Curve** | Low (standard Vivado workflow) |

### The Big Picture

This build system is **Project Mode**, but it's **automated Project Mode**:
- Gets convenience of Project Mode (GUI, IP management, incremental builds)
- Gets automation of Non-Project Mode (scriptable, reproducible, version-controllable)
- Trades disk space for build time and debuggability

**Best for**: Teams that want both automation and GUI access, using IP cores, with adequate disk space.

---

**Document Version**: 1.0  
**Last Updated**: 2026-09-12  
**Related**: MAKEFILE_BUILD_SYSTEM_ANALYSIS.md
