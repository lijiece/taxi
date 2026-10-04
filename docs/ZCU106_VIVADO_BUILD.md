# ZCU106 fpga_10g: Vivado build and source-file organization

This document traces the build in
[`src/eth/example/ZCU106/fpga/fpga_10g`](../src/eth/example/ZCU106/fpga/fpga_10g/Makefile).
GNU Make expands the `.f` source lists, generates Tcl scripts, and invokes
Vivado to create the project, synthesize, implement, and write the bitstream.
Vivado receives individual HDL filenames; it does not read these `.f` files
directly.

The flow was verified with a successful `make -n` dry run. Synthesis and
implementation were not run as part of this analysis.

## 1. How Make reads and evaluates Makefiles

Make first reads the Makefiles and records their variables and rules. It then
updates the requested target's prerequisites and executes the necessary
recipes. Conceptually, `include ../common/vivado.mk` inserts the shared file
at that location: Make reads the entire included file, then resumes reading
the board Makefile. It builds a combined representation in memory, without
creating a new Makefile on disk.

For `make program`, this means Make reads both files before selecting the
`program` rule. Its `fpga.bit` prerequisite can trigger the build rules from
`vivado.mk` before the programming recipe runs. Other target names are looked
up in the same combined set of rules; there is no special "not program"
branch. File targets that are up to date do not need their recipes executed.

### Immediate and deferred expansion

The surrounding context determines when an expression is evaluated.
`$(shell ...)` is **not inherently evaluated during reading**: it runs whenever
Make expands that expression.

```makefile
A := $(shell date)  # Runs now, while reading
B  = $(shell date)  # Stored now; runs whenever B is expanded
```

The main rules are:

| Construct | What happens while reading |
| --- | --- |
| `A := expression` or `A ::= expression` | Expand the value immediately |
| `A = expression` | Store the value for later expansion |
| `A ?= expression` | Check whether `A` is undefined; if so, store the value for later expansion |
| `A += expression` | Expand immediately if `A` is simply expanded (`:=` or `::=`); otherwise defer |
| `A != command` | Expand and execute the shell command immediately |
| Computed variable name, such as `FILES_$(MODE) = ...` | Expand the variable name immediately |
| `target: prerequisites` | Expand target and prerequisite expressions immediately |
| Recipe beneath a rule | Store it; defer expansion until the recipe is needed |
| `ifeq`, `ifneq`, `ifdef`, `ifndef` | Evaluate the conditional while reading |

`define` follows the assignment operator used; plain `define` defers its
body. GNU Make also supports `:::=`, which expands immediately and then
escapes dollar signs in the result. See the GNU Make manual's
[immediate/deferred expansion rules](https://www.gnu.org/s/make/manual/html_node/Reading-Makefiles.html).

Other important reading-time operations include:

- `include $(PATH)`: expand the filename expression and read the included
  Makefile.
- Standalone function calls, such as `$(info Reading configuration)` or
  `$(eval ...)`: evaluate when encountered. `eval` parses its generated text
  as Makefile content.
- Functions inside immediate expressions, including `wildcard`, `foreach`,
  `call`, and `shell`: evaluate as the enclosing expression is expanded.

These functions follow their individual argument-expansion rules; for
example, `$(if ...)` expands only the selected branch. See the
[GNU Make manual](https://www.gnu.org/s/make/manual/make.html) for details.

### Application to this build

```makefile
# Store an expression; do not expand it yet.
SYN_FILES = $(RTL_DIR)/fpga.sv

# Expand the old SYN_FILES, recursively read .f files,
# deduplicate, and store the resulting filenames now.
SYN_FILES := $(call uniq_base,$(call process_f_files,$(SYN_FILES)))

# Expand these filenames now to record prerequisites.
update_config.tcl: $(SYN_FILES)
	# Expand and execute this illustrative recipe only when needed.
	echo "..." > $@
```

Rule prerequisites capture values at the point where Make reads the rule,
while recipes can see later variable assignments:

```makefile
NAME = old

demo: $(NAME)
	@echo $(NAME)

NAME = new
```

Here, `demo` depends on `old`, but its recipe prints `new` if it runs. The
file `old` must exist or have a rule that can build it for this example to
reach the recipe.

An advanced exception is `.SECONDEXPANSION`, which allows specially escaped
prerequisite expressions to be expanded again later. This build does not use
that feature.

## 2. Build entry point

The [example Makefile](../src/eth/example/ZCU106/fpga/fpga_10g/Makefile) defines:

```makefile
FPGA_PART = xczu7ev-ffvc1156-2-e
FPGA_TOP = fpga
FPGA_ARCH = zynquplus

RTL_DIR = ../rtl
LIB_DIR = ../lib
TAXI_SRC_DIR = $(LIB_DIR)/taxi/src
```

It specifies four categories of inputs:

| Variable | Purpose in this example |
| --- | --- |
| `SYN_FILES` | Board RTL plus reusable modules and recursive `.f` lists |
| `XDC_FILES` | Board constraints and module-specific timing-constraint Tcl |
| `IP_TCL_FILES` | Tcl that creates the GTH transceiver IP |
| `CONFIG_TCL_FILES` | Tcl that sets top-level HDL parameters |

It then includes
[`../common/vivado.mk`](../src/eth/example/ZCU106/fpga/common/vivado.mk),
which implements the build machinery. `PROJECT` defaults to `FPGA_TOP`, so the
project is named `fpga`. The shared Makefile also optionally includes a local
`config.mk` before expanding the source lists.

The library paths are symlinks into the same checkout: the board's
`fpga/lib/taxi` points back to the repository root. Similarly,
`src/eth/lib/taxi` and `src/axis/lib/taxi` point back to the root. This lets
each subsystem express dependencies through its own `lib/taxi/src/...` path.

## 3. Recursive dependencies in `.f` files

The board Makefile lists the major components:

```makefile
SYN_FILES = $(RTL_DIR)/fpga.sv
SYN_FILES += $(RTL_DIR)/fpga_core.sv
SYN_FILES += $(TAXI_SRC_DIR)/eth/rtl/us/taxi_eth_mac_25g_us.f
SYN_FILES += $(TAXI_SRC_DIR)/xfcp/rtl/taxi_xfcp_if_uart.f
SYN_FILES += $(TAXI_SRC_DIR)/xfcp/rtl/taxi_xfcp_switch.sv
SYN_FILES += $(TAXI_SRC_DIR)/xfcp/rtl/taxi_xfcp_mod_apb.f
SYN_FILES += $(TAXI_SRC_DIR)/xfcp/rtl/taxi_xfcp_mod_stats.f
SYN_FILES += $(TAXI_SRC_DIR)/axis/rtl/taxi_axis_async_fifo.f
SYN_FILES += $(TAXI_SRC_DIR)/sync/rtl/taxi_sync_reset.sv
SYN_FILES += $(TAXI_SRC_DIR)/sync/rtl/taxi_sync_signal.sv
SYN_FILES += $(TAXI_SRC_DIR)/io/rtl/taxi_debounce_switch.sv
```

A `.f` file is a plain list of paths. Each path is interpreted **relative to
the directory containing that `.f` file**, and can name either HDL or another
`.f` file.

For example,
[`taxi_eth_mac_25g_us.f`](../src/eth/rtl/us/taxi_eth_mac_25g_us.f) contains:

```text
taxi_eth_mac_25g_us.sv
taxi_eth_mac_25g_us_ch.sv
taxi_eth_phy_25g_us_gt.f
taxi_eth_phy_25g_us_gt_ll.f
taxi_eth_phy_10g_us_gt.f
taxi_eth_phy_10g_us_gt_ll.f
taxi_eth_phy_10g_7_gt.f
../taxi_eth_mac_phy_10g.f
../taxi_eth_mac_10g.f
../taxi_eth_phy_10g.f
../../lib/taxi/src/apb/rtl/taxi_apb_interconnect_1s.sv
```

A partial dependency tree is:

```text
fpga_10g/Makefile
├── ../rtl/fpga.sv
├── ../rtl/fpga_core.sv
├── taxi_eth_mac_25g_us.f
│   ├── taxi_eth_mac_25g_us.sv
│   ├── taxi_eth_mac_25g_us_ch.sv
│   ├── taxi_eth_phy_10g_us_gt_ll.f
│   │   └── transceiver wrapper and supporting RTL
│   ├── taxi_eth_mac_phy_10g.f
│   │   ├── taxi_eth_mac_phy_10g.sv
│   │   ├── taxi_eth_mac_phy_10g_rx.f
│   │   └── taxi_eth_mac_phy_10g_tx.f
│   └── other supported MAC/PHY implementations
├── taxi_xfcp_if_uart.f
└── taxi_axis_async_fifo.f
    ├── taxi_axis_async_fifo.sv
    ├── taxi_sync_reset.sv
    ├── taxi_sync_signal.sv
    └── taxi_axis_if.sv
```

This organization keeps a reusable component's dependencies beside its RTL.
A board build can include the component's `.f` rather than manually
reproducing its transitive dependencies.

## 4. How Make expands the lists

The implementation in
[`vivado.mk`](../src/eth/example/ZCU106/fpga/common/vivado.mk) is:

```makefile
process_f_file = $(call process_f_files,$(addprefix $(dir $1),$(shell cat $1)))
process_f_files = $(foreach f,$1,$(if $(filter %.f,$f),$(call process_f_file,$f),$f))
uniq_base = $(if $1,$(call uniq_base,$(foreach f,$1,$(if $(filter-out $(notdir $(lastword $1)),$(notdir $f)),$f,))) $(lastword $1))
SYN_FILES := $(call uniq_base,$(call process_f_files,$(SYN_FILES)))
INC_FILES := $(call uniq_base,$(call process_f_files,$(INC_FILES)))
```

For each entry, Make:

1. Checks whether its name ends in `.f`.
2. If so, reads its contents and prefixes every entry with that list's directory.
3. Recursively expands any nested `.f`.
4. Otherwise, retains the entry as a source path.
5. Deduplicates the flattened list using `uniq_base`.

**Deduplication compares basenames, not complete paths, and the last occurrence
wins.** For example:

```text
some/path/taxi_sync_reset.sv
another/path/taxi_sync_reset.sv
```

becomes:

```text
another/path/taxi_sync_reset.sv
```

This removes repeated dependencies introduced by multiple components and
different symlink paths. It also means two distinct files with the same
filename cannot both survive expansion. Appending a replacement source with
the same basename overrides an earlier source.

The parser splits on whitespace and does not implement simulator-style `-f`,
`+incdir+`, comments, quoted filenames, or cycle detection. Use plain relative
paths, conventionally one per line. The immediate `:=` assignments perform
expansion while Make reads the Makefiles, before Vivado starts.

## 5. Creating the Vivado project

The project-creation rule generates `create_project.tcl`. Its essential
content is shown below; angle-bracket lists represent expanded filenames:

```tcl
create_project -force -part xczu7ev-ffvc1156-2-e fpga
add_files -fileset sources_1 defines.v <expanded HDL filenames>
set_property top fpga [current_fileset]
add_files -fileset constrs_1 <board and module constraints>
source ../lib/taxi/src/eth/rtl/us/taxi_eth_phy_10g_us_gth_156.tcl
source ./config.tcl
```

The dry run confirmed that the HDL list contains individual `.sv` paths, with
no `.f` entries.

- `defines.v` is generated from the Make variable `DEFS`.
- Constraint Tcl files in `XDC_FILES` are added to `constrs_1`.
- IP and configuration Tcl files are executed with `source`.
- If supplied, `XCI_FILES` are imported with `import_ip`; this example does not
  specify any.
- `INC_FILES` participates in dependency tracking, but this rule does not
  separately add it to the project or configure include directories.

The [IP script](../src/eth/rtl/us/taxi_eth_phy_10g_us_gth_156.tcl) creates four
GT Wizard variants: normal/low latency, each with either channel-plus-common
or channel-only. Their names are:

```text
taxi_eth_phy_10g_us_gth_full
taxi_eth_phy_10g_us_gth_ch
taxi_eth_phy_10g_us_gth_ll_full
taxi_eth_phy_10g_us_gth_ll_ch
```

It specifies a 10.3125 Gb/s line rate, 156.25 MHz reference clock, and 32-bit
user datapath.

The [configuration script](../src/eth/example/ZCU106/fpga/fpga_10g/config.tcl)
sets:

```text
CFG_LOW_LATENCY = 1
COMBINED_MAC_PCS = 1
MAC_DATA_W = 32
```

These become top-level parameters through `set_property generic` on
`sources_1`.

Despite the name `taxi_eth_mac_25g_us`, this wrapper also supports the 10G
configuration used here.
[`fpga_core.sv`](../src/eth/example/ZCU106/fpga/rtl/fpga_core.sv) instantiates
it with two channels and `GT_TYPE("GTH")`. The `.f` includes a broader set of
supported implementations; HDL parameterization selects the active hardware.
Source-list membership is therefore broader than the instantiated hardware
hierarchy.

## 6. Synthesis, implementation, and output generation

The build rules form this chain:

```text
create_project.tcl + update_config.tcl
                   ↓
                fpga.xpr
                   ↓  run_synth.tcl
       fpga.runs/synth_1/fpga.dcp
                   ↓  run_impl.tcl
    fpga.runs/impl_1/fpga_routed.dcp
                   ↓  generate_bit.tcl
          fpga.bit / fpga.bin / fpga.xsa
```

`update_config.tcl` opens the project and sources the configuration script.
The `.xpr` rule invokes Vivado in batch mode with whichever project/config
scripts are newer than the project. On a fresh build, the command is:

```bash
vivado -nojournal -nolog -mode batch \
    -source create_project.tcl -source update_config.tcl
```

Synthesis opens the project, resets and launches `synth_1`, then waits for
completion. Implementation does the same for `impl_1`, opens the implemented
design, and writes flat and hierarchical utilization reports. Both use
`launch_runs -jobs 4`.

The final script opens the implemented design and runs:

```tcl
write_bitstream -force -bin_file fpga.runs/impl_1/fpga.bit
write_debug_probes -force fpga.runs/impl_1/fpga.ltx
write_hw_platform -fixed -force -include_bit fpga.xsa
```

The Makefile creates convenient symlinks to `.bit` and `.bin`, and to `.ltx`
if present. It archives outputs under `rev/`, starting with `fpga_rev100.*`
and selecting the next unused revision number on subsequent builds.

From the repository root, with Vivado available in `PATH`:

```bash
cd src/eth/example/ZCU106/fpga/fpga_10g

make -n       # Preview the build commands
make fpga.xpr # Create/update the project
make vivado   # Create/update the project and open the GUI
make          # Build through bitstream generation
make program  # Build if necessary, then program the board
```

The `program` target generates a hardware-manager Tcl script and programs
the first device returned by `get_hw_devices`.

## 7. Rebuild behavior and the `.f` dependency limitation

The `.f` files are read whenever Make parses the Makefile, but **the `.f`
files themselves are not retained as build prerequisites**.

| Change | Behavior encoded in the Makefile |
| --- | --- |
| Existing HDL or constraint changes | Update configuration and rerun synthesis/implementation |
| `config.tcl` changes | Reapply parameters and rebuild |
| Board `Makefile` or IP Tcl changes | Regenerate project-creation Tcl and rebuild |
| Only `.f` membership changes | Does not reliably regenerate the project's source list |

Even if adding a source triggers synthesis, the existing project may still
lack that source because only `create_project.tcl` contains `add_files`.
Removing a source from a `.f` can likewise leave the old file in the project.
The shared `vivado.mk` itself is also not listed as a prerequisite of
`create_project.tcl`.

After changing `.f` membership, explicitly force project regeneration. For
example, from `fpga_10g`:

```bash
touch Makefile
make
```

A clean rebuild is another option. `make clean` removes generated project
files and current outputs but preserves the `rev/` archive; `make distclean`
also removes that archive.

A robust build-system improvement would track all visited `.f` files as
prerequisites of `create_project.tcl`, along with the shared `vivado.mk`.

## 8. Walkthrough of `vivado.mk`, starting at line 39

This section follows
[`vivado.mk`](../src/eth/example/ZCU106/fpga/common/vivado.mk) in source order.
Line numbers refer to the version examined for this document.

### Lines 39–44: action targets and file preservation

```makefile
.PHONY: fpga vivado tmpclean clean distclean
.PRECIOUS: %.xpr %.bit %.bin %.ltx %.xsa %.mcs %.prm
.SECONDARY:
```

`.PHONY` declares names that represent actions rather than files. For
example, `make vivado` must open the GUI even if a file named `vivado` exists.
Making `fpga` phony does not force its bitstream prerequisite to rebuild:
Make still checks whether that file is up to date.

`program` is not declared phony in the current board Makefile or shared file.
It normally works because no file named `program` exists. To make its behavior
reliable, the board Makefile could add the following beside its programming
rule:

```makefile
.PHONY: program
```

Multiple `.PHONY` declarations accumulate; this would add to the shared list,
not replace it. This is a suggested improvement, not a change made by this
document.

`.PRECIOUS` protects matching targets from Make's automatic deletion on
interruption and from intermediate-file cleanup. `%` is the pattern wildcard;
for example, `%.bit` matches `fpga.bit`.

`.SECONDARY` can name specific intermediate files to retain:

```makefile
.SECONDARY: intermediate.dcp generated.v
```

With no prerequisites, as used here, it prevents automatic deletion of all
intermediate files. Make typically identifies intermediate files while
constructing implicit-rule chains. For example, given rules to generate
`%.c` from `%.y` and compile `%.o` from `%.c`, Make can infer:

```text
parser.y → parser.c → parser.o
```

The inferred `parser.c` may normally be deleted after use. `.SECONDARY:`
retains it. Being in the middle of a dependency graph does not by itself
make a file intermediate; the explicitly named checkpoints and scripts in
this build generally do not require that protection.

Neither `.PRECIOUS` nor `.SECONDARY` prevents explicit removal by a cleanup
recipe.

### Lines 46–51: optional configuration and defaults

```makefile
CONFIG ?= config.mk
-include $(CONFIG)

FPGA_TOP ?= fpga
PROJECT ?= $(FPGA_TOP)
XDC_FILES ?= $(PROJECT).xdc
```

`?=` supplies a default only when a variable is undefined. An explicitly
defined empty value also counts as defined.

`-include` reads the selected configuration file if available and tolerates
its absence. For example, `make CONFIG=local.mk` selects a different file.
This is a Make configuration file, distinct from the Vivado Tcl file
`config.tcl`.

The remaining defaults choose a top module, project name, and constraint
filename. The board Makefile already supplies `FPGA_TOP` and `XDC_FILES`, so
those defaults do not replace its settings. `PROJECT` defaults to `fpga` in
this example but can differ from the HDL top module name.

### Lines 53–58: expand source manifests

The `process_f_file` and `process_f_files` variables contain callable Make
expressions. They are defined with `=`, so defining them does not immediately
read any `.f` files.

The subsequent assignments trigger expansion:

```makefile
SYN_FILES := $(call uniq_base,$(call process_f_files,$(SYN_FILES)))
INC_FILES := $(call uniq_base,$(call process_f_files,$(INC_FILES)))
```

They recursively read manifests, prefix entries with each manifest's
directory, and deduplicate by basename with the last occurrence winning.
Section 4 explains the functions in detail. Expansion happens for any
requested target, including `clean`, because it occurs while reading the
Makefiles.

### Lines 60–76: public build and GUI targets

```makefile
all: fpga

fpga: $(PROJECT).bit

vivado: $(PROJECT).xpr
	vivado $(PROJECT).xpr
```

`all` is the first ordinary target in this shared file. In the supplied
configuration, it becomes the default goal when running plain `make`.
The chain `all → fpga → fpga.bit` requests the bitstream; the first two
targets need no recipes of their own.

`vivado` ensures that the project exists and is updated, then opens it in
the GUI. It does not request synthesis or bitstream generation.

### Lines 78–87: cleanup levels

```makefile
tmpclean::
	-rm -rf *.log *.jou *.cache *.gen *.hbs *.hw *.ip_user_files *.runs *.xpr *.html *.xml *.sim *.srcs *.str .Xil defines.v
	-rm -rf create_project.tcl update_config.tcl run_synth.tcl run_impl.tcl generate_bit.tcl

clean:: tmpclean
	-rm -rf *.bit *.bin *.ltx *.xsa program.tcl generate_mcs.tcl *.mcs *.prm flash.tcl
	-rm -rf *_utilization.rpt *_utilization_hierarchical.rpt

distclean:: clean
	-rm -rf rev
```

| Target | Effect |
| --- | --- |
| `tmpclean` | Remove generated project/run directories, logs, generated build Tcl, and `defines.v` |
| `clean` | Run `tmpclean`, then remove current output files, programming scripts, and utilization reports |
| `distclean` | Run `clean`, then remove the `rev/` archive |

The double-colon syntax, such as `clean:: tmpclean`, allows other Makefiles
to add independent double-colon rules and recipes for the same target.
Extensions must also use `::`; ordinary `:` and `::` rules cannot be mixed
for one target.

The leading `-` in a recipe such as `-rm -rf ...` tells Make to ignore an
error from that command. It is Make syntax, separate from the shell command's
own `-rf` options.

### Lines 95–106: generate the project-creation Tcl

```makefile
create_project.tcl: Makefile $(XCI_FILES) $(IP_TCL_FILES)
	rm -rf defines.v
	touch defines.v
	for x in $(DEFS); do echo '`define' $$x >> defines.v; done
	echo "create_project -force -part $(FPGA_PART) $(PROJECT)" > $@
	echo "add_files -fileset sources_1 defines.v $(SYN_FILES)" >> $@
	echo "set_property top $(FPGA_TOP) [current_fileset]" >> $@
	echo "add_files -fileset constrs_1 $(XDC_FILES)" >> $@
	for x in $(XCI_FILES); do echo "import_ip $$x" >> $@; done
	for x in $(IP_TCL_FILES); do echo "source $$x" >> $@; done
	for x in $(CONFIG_TCL_FILES); do echo "source $$x" >> $@; done
```

The recipe runs when the script is missing or a listed prerequisite is newer.
It recreates `defines.v`, writes macro definitions from `DEFS`, then writes
Tcl to create the project, add HDL and constraints, import existing IP,
generate scripted IP, and apply configuration.

The recipe has the following steps:

1. Remove and recreate `defines.v`, so old macro definitions cannot survive
   project regeneration. It remains an empty source file when `DEFS` is empty.
   The single quotes around the literal Verilog `` `define `` prevent the
   shell from interpreting its backtick as command substitution.
2. Start a new Tcl file with `create_project`. `-part` selects the FPGA device;
   `-force` permits overwriting an existing project. In this example the
   generated command is `create_project -force -part xczu7ev-ffvc1156-2-e fpga`.
3. Add `defines.v` and the already expanded HDL paths to `sources_1`.
4. Set the top-level HDL module on the current fileset. This is `fpga`, even
   if a configuration chooses a different project filename.
5. Add board constraints and constraint Tcl files to `constrs_1`.
6. Append one `import_ip` command per existing XCI file. The loop has no
   iterations in this example because `XCI_FILES` is empty.
7. Append one `source` command per IP-generation script, then per configuration
   script. This ordering creates the IP before applying the final project
   configuration.

Several syntax layers meet here:

| Syntax | Interpreter and meaning |
| --- | --- |
| `$(PROJECT)` | Make variable expansion |
| `$@` | Make automatic variable: the current target, here `create_project.tcl` |
| `$$x` | Make emits `$x`, which the shell expands as its loop variable |
| `>` / `>>` | Shell redirection: replace / append to the generated file |
| `[current_fileset]` | Tcl command substitution, evaluated later by Vivado |

The `echo` commands only write Tcl text. They do not create the Vivado project
themselves. The literal `Makefile` prerequisite also means renaming the entry
Makefile requires updating this dependency, even if invoking Make with `-f`.

Each ordinary recipe line runs in its own shell. The generated files persist
between those shells, and each `for ...; do ...; done` loop is contained in
one line. Square brackets inside the double-quoted `echo` arguments are
written as text; Tcl evaluates them when Vivado later sources the script.

### Lines 108–114: refresh configuration and run project Tcl

```makefile
update_config.tcl: $(CONFIG_TCL_FILES) $(SYN_FILES) $(INC_FILES) $(XDC_FILES)
	echo "open_project -quiet $(PROJECT).xpr" > $@
	for x in $(CONFIG_TCL_FILES); do echo "source $$x" >> $@; done

$(PROJECT).xpr: create_project.tcl update_config.tcl
	vivado -nojournal -nolog -mode batch $(foreach x,$?,-source $x)
```

The configuration script is regenerated when the listed inputs change. It
opens the existing project and sources the configuration Tcl files; it does
not add or remove HDL sources.

`$?` expands to prerequisites newer than the target, or all prerequisites
when the target does not exist. `foreach` turns those names into `-source`
arguments. A fresh build therefore runs both scripts; an ordinary source
edit can run only `update_config.tcl`.

For this board, the generated update script is simply:

```tcl
open_project -quiet fpga.xpr
source ./config.tcl
```

The distinction between `$x` and `$$x` is intentional: in
`$(foreach x,$?,-source $x)`, `x` is a Make variable, so Make expands `$x`
itself. In the shell loops above, `$$x` preserves the dollar sign for the
shell. On a fresh build, the project recipe expands to:

```bash
vivado -nojournal -nolog -mode batch \
    -source create_project.tcl -source update_config.tcl
```

`-mode batch` runs without the GUI, while `-nojournal` and `-nolog` suppress
the invocation's journal and log files. Vivado's managed runs can still
produce their own run logs and reports.

### Lines 116–122: synthesis checkpoint

```makefile
$(PROJECT).runs/synth_1/$(PROJECT).dcp: create_project.tcl update_config.tcl $(SYN_FILES) $(INC_FILES) $(XDC_FILES) | $(PROJECT).xpr
	echo "open_project $(PROJECT).xpr" > run_synth.tcl
	echo "reset_run synth_1" >> run_synth.tcl
	echo "launch_runs -jobs 4 synth_1" >> run_synth.tcl
	echo "wait_on_run synth_1" >> run_synth.tcl
	vivado -nojournal -nolog -mode batch -source run_synth.tcl
```

The dependencies before `|` are ordinary prerequisites: newer timestamps
can cause synthesis to rerun. The project after `|` is an **order-only
prerequisite**: Make must update it first, but its timestamp alone does not
invalidate the synthesis checkpoint.

The recipe generates `run_synth.tcl`, which opens the project, resets
`synth_1`, launches it with `-jobs 4`, and waits for completion. It then runs
that script in a separate Vivado batch invocation. Make tracks the resulting
`.dcp` as the target, rather than the generated Tcl script.

`open_project` loads the project in this new Vivado process. `reset_run`
invalidates the previous synthesis run so the launch performs a new run.
`launch_runs` starts the managed run, and `wait_on_run` keeps the script from
finishing while synthesis is still in progress. `-jobs 4` controls Vivado's
run-job concurrency; it is separate from GNU Make's `-j` setting.

The target is `fpga.runs/synth_1/fpga.dcp` with the default project name.
If that checkpoint is missing, or an ordinary prerequisite is newer, Make
runs this recipe. A change to the `.xpr` timestamp alone does not force it.
The rule contains no explicit Tcl status assertion after `wait_on_run`; the
wait command should not be read as an additional success check implemented
by this Makefile.

### Lines 124–133: implementation checkpoint and reports

```makefile
$(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp: $(PROJECT).runs/synth_1/$(PROJECT).dcp
	echo "open_project $(PROJECT).xpr" > run_impl.tcl
	echo "reset_run impl_1" >> run_impl.tcl
	echo "launch_runs -jobs 4 impl_1" >> run_impl.tcl
	echo "wait_on_run impl_1" >> run_impl.tcl
	echo "open_run impl_1" >> run_impl.tcl
	echo "report_utilization -file $(PROJECT)_utilization.rpt" >> run_impl.tcl
	echo "report_utilization -hierarchical -file $(PROJECT)_utilization_hierarchical.rpt" >> run_impl.tcl
	vivado -nojournal -nolog -mode batch -source run_impl.tcl
```

The routed checkpoint depends on the synthesis checkpoint. When needed,
Make generates and executes `run_impl.tcl` to:

1. Open the project and reset `impl_1`.
2. Launch implementation with `-jobs 4` and wait for completion.
3. Open the implemented design.
4. Write flat and hierarchical utilization reports.

The routed `.dcp` is the tracked target. The reports are outputs of its
recipe, not separately tracked targets; deleting only a report does not
automatically force its regeneration.

`open_project` loads the project metadata; `open_run impl_1` subsequently
loads the implemented design so the reports describe that result. The first
report summarizes resource use, while `-hierarchical` breaks resource use
down by design hierarchy. The script delegates implementation to Vivado's
managed `impl_1` run rather than calling placement and routing commands
directly. Bitstream writing is handled by the next recipe.

### Lines 135–153: bitstream, hardware platform, and archive

```makefile
$(PROJECT).bit $(PROJECT).bin $(PROJECT).ltx $(PROJECT).xsa: $(PROJECT).runs/impl_1/$(PROJECT)_routed.dcp
	echo "open_project $(PROJECT).xpr" > generate_bit.tcl
	echo "open_run impl_1" >> generate_bit.tcl
	echo "write_bitstream -force -bin_file $(PROJECT).runs/impl_1/$(PROJECT).bit" >> generate_bit.tcl
	echo "write_debug_probes -force $(PROJECT).runs/impl_1/$(PROJECT).ltx" >> generate_bit.tcl
	echo "write_hw_platform -fixed -force -include_bit $(PROJECT).xsa" >> generate_bit.tcl
	vivado -nojournal -nolog -mode batch -source generate_bit.tcl
	ln -f -s $(PROJECT).runs/impl_1/$(PROJECT).bit .
	ln -f -s $(PROJECT).runs/impl_1/$(PROJECT).bin .
	if [ -e $(PROJECT).runs/impl_1/$(PROJECT).ltx ]; then ln -f -s $(PROJECT).runs/impl_1/$(PROJECT).ltx .; fi
	mkdir -p rev
	COUNT=100; \
	while [ -e rev/$(PROJECT)_rev$$COUNT.bit ]; \
	do COUNT=$$((COUNT+1)); done; \
	cp -pv $(PROJECT).runs/impl_1/$(PROJECT).bit rev/$(PROJECT)_rev$$COUNT.bit; \
	cp -pv $(PROJECT).runs/impl_1/$(PROJECT).bin rev/$(PROJECT)_rev$$COUNT.bin; \
	if [ -e $(PROJECT).runs/impl_1/$(PROJECT).ltx ]; then cp -pv $(PROJECT).runs/impl_1/$(PROJECT).ltx rev/$(PROJECT)_rev$$COUNT.ltx; fi; \
	if [ -e $(PROJECT).xsa ]; then cp -pv $(PROJECT).xsa rev/$(PROJECT)_rev$$COUNT.xsa; fi
```

The recipe writes and runs `generate_bit.tcl` to open the implemented design,
write the bitstream and binary, write debug probes, and export the hardware
platform with its bitstream. It then creates output symlinks and copies the
outputs into `rev/` under the next unused revision number, starting at 100.

The Tcl commands produce the following artifacts:

| Command | Purpose and output |
| --- | --- |
| `open_project` followed by `open_run impl_1` | Load the project and its implemented design |
| `write_bitstream -force -bin_file ...` | Write `fpga.runs/impl_1/fpga.bit` and its companion `.bin`, allowing replacement |
| `write_debug_probes -force ...` | Write debug-probe metadata to `.ltx` when applicable |
| `write_hw_platform -fixed -force -include_bit ...` | Export a fixed hardware platform as `fpga.xsa`, including the bitstream |

After Vivado returns, `ln -f -s ... .` creates or replaces symbolic links in
the working directory. Thus `fpga.bit` and `fpga.bin` point into the
implementation-run directory instead of duplicating those files. The `.ltx`
link is conditional on the file existing. The `.xsa` is already written in
the working directory and needs no link.

`mkdir -p rev` creates the archive directory if necessary. The loop tests
`rev/fpga_rev100.bit`, then 101, and so on, until it finds an unused bitstream
name. The copy commands use the same number for every artifact from that
execution. `cp -p` preserves source attributes such as timestamps, and `-v`
prints the copy operations. These revision numbers are local archive numbers,
not Git commit identifiers.

The backslash-continued archive commands run together in one shell so that
the shell variable `COUNT` persists across the loop and copy commands. Make's
`$$COUNT` becomes the shell's `$COUNT`.

Similarly, `$$((COUNT+1))` becomes the shell arithmetic expression
`$((COUNT+1))`. The `if [ -e ... ]` tests are shell file-existence checks,
not Make conditionals. Semicolons separate commands in this one shell; the
block does not explicitly enable fail-fast handling for each copy operation.

This is an ordinary multiple-target `:` rule, not a grouped `&:` rule.
Although one execution produces several outputs, Make treats the listed
targets independently. Requesting several missing outputs together can
therefore execute the recipe more than once, potentially concurrently with
parallel Make. The normal `make` path requests only the `.bit` target. An
improved build could explicitly model the outputs as one generation step.

The Make syntax described here is documented in the GNU Make manual's
[special targets](https://www.gnu.org/software/make/manual/html_node/Special-Targets.html),
[prerequisite types](https://www.gnu.org/software/make/manual/html_node/Prerequisite-Types.html),
and [multiple targets](https://www.gnu.org/software/make/manual/html_node/Multiple-Targets.html)
sections.
