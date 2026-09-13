# Vivado Project Mode - Quick Reference Card

## At a Glance

**Yes, this uses Project Mode.** You'll see these directories:

```bash
$ ls -d fpga.*
fpga.xpr          # ← PROJECT FILE
fpga.cache/       # ← IP cache
fpga.gen/         # ← Generated IP  
fpga.hw/          # ← Hardware manager
fpga.ip_user_files/
fpga.runs/        # ← BUILD OUTPUTS (bitstream here!)
fpga.sim/
fpga.srcs/
```

---

## Project Directories Explained

| Directory | Purpose | Size (Typical) | Keep in Git? |
|-----------|---------|----------------|--------------|
| `fpga.xpr` | Project file (XML) | 50 KB | ❌ No (regenerated) |
| `fpga.cache/` | IP cache | 3-150 MB | ❌ No |
| `fpga.gen/` | Generated IP RTL | 10-500 MB | ❌ No |
| `fpga.hw/` | Hardware manager | 10 KB - 1 MB | ❌ No |
| `fpga.ip_user_files/` | IP user files | 10 KB | ❌ No |
| `fpga.runs/` | **Build outputs** | 50 MB - 5 GB | ❌ No |
| `fpga.sim/` | Simulation files | 1 MB - 10 GB | ❌ No |
| `fpga.srcs/` | Source management | 1-10 MB | ❌ No |

### Where's My Bitstream?
```bash
fpga.runs/impl_1/fpga.bit    # ← HERE!
```

Symlinked to top level:
```bash
fpga.bit -> fpga.runs/impl_1/fpga.bit
```

---

## Disk Usage Example

**ZCU106 10G design** (small):
```bash
$ du -sh fpga.*
48M     fpga.runs/        ← Biggest
14M     fpga.gen/         ← Generated IP
3.3M    fpga.cache/       ← IP cache
536K    fpga.srcs/
428K    fpga.xsa/         ← Hardware platform
48K     fpga.xpr/         ← Project file
8K      fpga.hw/
4K      fpga.sim/
--------------------------
Total:  ~66 MB
```

**U280 100G design** (large):
```bash
fpga.runs/        2.5 GB  ← Much larger!
fpga.gen/         450 MB
fpga.cache/       150 MB
...
--------------------------
Total:  ~3.5 GB
```

---

## What to Track in Git

### ✅ DO Track
```bash
Makefile                  # Build config
config.tcl                # Parameters
../rtl/*.sv              # Your RTL
../syn/*.xdc             # Constraints
../lib/                  # Libraries (if local)
```

### ❌ DON'T Track
```bash
fpga.xpr                 # Project file (regenerated)
fpga.cache/
fpga.gen/
fpga.hw/
fpga.ip_user_files/
fpga.runs/               # ← Build outputs!
fpga.sim/
fpga.srcs/
*.log, *.jou             # Vivado logs
defines.v                # Generated
create_project.tcl       # Generated
run_*.tcl                # Generated
```

### 📦 Optionally Track
```bash
rev/                     # Archived builds (if you want)
rev/fpga_rev100.bit
```

---

## .gitignore Template

```gitignore
# Vivado Project Mode
*.xpr
*.cache/
*.gen/
*.hw/
*.ip_user_files/
*.runs/
*.sim/
*.srcs/

# Vivado logs
*.log
*.jou
*.str
.Xil/

# Generated files
defines.v
create_project.tcl
update_config.tcl
run_synth.tcl
run_impl.tcl
generate_bit.tcl
program.tcl

# Output files (unless archiving)
*.bit
*.bin
*.ltx
*.xsa
*.mcs
*.prm

# Keep archived builds (optional)
!rev/*.bit
!rev/*.bin
```

---

## Common Commands

### Build
```bash
make              # Build bitstream
```

### Open in GUI
```bash
make vivado       # Opens fpga.xpr in Vivado GUI
```

### Clean
```bash
make tmpclean     # Remove project dirs, keep outputs
make clean        # Remove project dirs AND outputs
make distclean    # Remove everything including rev/
```

### Program
```bash
make program      # Program FPGA (if target exists)
```

---

## Where Things Live

### Your Sources (Version Controlled)
```
../rtl/fpga.sv
../rtl/fpga_core.sv
../syn/fpga.xdc
```

### Generated Project
```
fpga.xpr                    ← References your sources
fpga.srcs/sources_1/        ← But doesn't copy them
```

### Build Outputs
```
fpga.runs/
├── synth_1/
│   └── fpga.dcp            ← Post-synthesis
└── impl_1/
    ├── fpga_routed.dcp     ← Post-route
    ├── fpga.bit            ← BITSTREAM!
    ├── fpga.bin
    └── *.rpt               ← Reports
```

### Archived Builds
```
rev/
├── fpga_rev100.bit
├── fpga_rev101.bit
└── ...
```

---

## Troubleshooting

### "Out of disk space"
```bash
# Check usage
du -sh fpga.*

# Clean old builds
make clean

# Or remove entire project
rm -rf fpga.*
make              # Rebuild from scratch
```

### "Project file corrupted"
```bash
# Delete and regenerate
rm fpga.xpr
make              # Recreates from Makefile
```

### "IP not found"
```bash
# Clean IP cache
rm -rf fpga.cache fpga.gen
make              # Regenerates IP
```

### "Can't find output file"
```bash
# Build didn't complete?
ls -la fpga.runs/impl_1/fpga.bit

# Check logs
tail fpga.runs/impl_1/runme.log
```

---

## Key Takeaways

1. **Project Mode**: Uses `.xpr` file + managed directories
2. **Automated**: Makefile regenerates project from sources
3. **GUI Available**: `make vivado` for debugging
4. **Disk Hungry**: ~100 MB to several GB per build
5. **Git Friendly**: Only track sources, project is throwaway
6. **Build Outputs**: In `fpga.runs/impl_1/`
7. **Cleaning**: `make clean` removes all generated files

---

## Quick Comparison

| Aspect | Project Mode | Non-Project Mode |
|--------|--------------|------------------|
| **This System** | ✅ YES | ❌ No |
| **Project File** | ✅ fpga.xpr | ❌ None |
| **GUI Access** | ✅ `make vivado` | ❌ Limited |
| **Disk Usage** | ⚠️ High | ✅ Low |
| **IP Management** | ✅ Automatic | ⚠️ Manual |
| **Automation** | ✅ Via Makefile | ✅ Via TCL |

---

## More Information

- **Full Details**: [VIVADO_PROJECT_MODE_EXPLAINED.md](VIVADO_PROJECT_MODE_EXPLAINED.md)
- **Build System**: [MAKEFILE_BUILD_SYSTEM_ANALYSIS.md](MAKEFILE_BUILD_SYSTEM_ANALYSIS.md)

---

**Quick Ref Version**: 1.0  
**Last Updated**: 2026-09-12
