# ZCU106 GPIO Guide - Buttons, Switches, and LEDs

## Current Design Usage

### LEDs (8x Green LEDs)
**Location**: Top edge of board, near center
**Silkscreen**: LED0-LED7 (or DS50-DS57)
**Current Function**: **Switch mirror** - LEDs directly reflect DIP switch positions

```verilog
assign led = sw;  // LED[7:0] = SW[7:0]
```

**What you'll see**:
- LED ON = corresponding switch is ON (up position)
- LED OFF = corresponding switch is OFF (down position)
- Real-time feedback showing switch state

**Physical locations** (from constraints):
- LED[0] - AL11 (leftmost)
- LED[1] - AL13
- LED[2] - AK13
- LED[3] - AE15
- LED[4] - AM8
- LED[5] - AM9
- LED[6] - AM10
- LED[7] - AM11 (rightmost)

---

### DIP Switches (8-position DIP switch)
**Location**: Lower-left area of board
**Silkscreen**: SW2 or SW4 (depends on board revision)
**Current Function**: User input, mirrored to LEDs

**Physical locations**:
- SW[0] - A17 (position 1)
- SW[1] - A16 (position 2)
- SW[2] - B16 (position 3)
- SW[3] - B15 (position 4)
- SW[4] - A15 (position 5)
- SW[5] - A14 (position 6)
- SW[6] - B14 (position 7)
- SW[7] - B13 (position 8)

**How to use**:
```
ON (up) = logic '1'
OFF (down) = logic '0'
```

**Current behavior**: Simply controls which LEDs are on/off

---

### Push Buttons (5x tactile buttons)
**Location**: Near center of board, arranged in cross pattern
**Silkscreen**: BTN-U, BTN-L, BTN-D, BTN-R, BTN-C
**Current Function**: **NOT USED** (inputs debounced but not connected to any logic)

**Layout**:
```
       [BTN-U]
          ↑
[BTN-L] ← [BTN-C] → [BTN-R]
          ↓
       [BTN-D]
```

**Physical locations**:
- BTN-U (Up)     - AG13
- BTN-L (Left)   - AK12
- BTN-D (Down)   - AP20
- BTN-R (Right)  - AC14
- BTN-C (Center) - AL10

**Note**: The design includes debouncing logic, so the buttons are ready to use if you want to modify the design.

---

### Reset Button (CPU_RESET)
**Location**: Lower-right corner of board
**Silkscreen**: CPU_RESET or SW6
**Current Function**: System reset (active LOW)

**Physical location**: G13

**Behavior**:
- Press and hold = Reset asserted (system in reset)
- Release = System runs normally
- Used to reset the entire FPGA design

---

## Board Layout (ZCU106)

```
  ┌────────────────────────────────────────────────────────┐
  │                    ZCU106 FPGA Board                    │
  │                                                          │
  │  [USB]  [JTAG]      [LEDs: ████████]        [SFP+][SFP+]│  ← Top edge
  │                      LED0-LED7                Port0 Port1│
  │                                                          │
  │                                                          │
  │  [FMC HPC0]              [BTN-U]                        │
  │                             ↑                            │
  │               [BTN-L] ← [BTN-C] → [BTN-R]               │
  │                             ↓                            │
  │                          [BTN-D]                         │
  │                                                          │
  │  [FMC HPC1]                                    [RESET]  │  ← CPU_RESET
  │                                                          │
  │  [DIP SW]                                                │  ← SW2/SW4
  │   12345678                                               │     (8 positions)
  │                                                          │
  └────────────────────────────────────────────────────────┘

Legend:
  [USB]     - USB UART (CP2108 quad UART, channel 2 for XFCP)
  [JTAG]    - JTAG programming connector
  [SFP+]    - 10G Ethernet SFP+ cages
  [FMC...]  - FMC expansion connectors
  [DIP SW]  - 8-position DIP switch
  [RESET]   - Push button for system reset
```

---

## Quick Test Procedure

### Test 1: Verify LEDs mirror switches
```
1. Look at the 8 LEDs on top of the board
2. Flip DIP switches on/off
3. Corresponding LEDs should immediately turn on/off
```

**Example**:
```
Switch position:  ↑ ↓ ↑ ↑ ↓ ↓ ↑ ↓    (↑=ON, ↓=OFF)
                  7 6 5 4 3 2 1 0
Expected LEDs:    █ ░ █ █ ░ ░ █ ░    (█=ON, ░=OFF)
```

### Test 2: Reset the design
```
1. Press and hold CPU_RESET button
2. All LEDs should turn off (system in reset)
3. Release CPU_RESET
4. LEDs should return to showing switch state
```

---

## Common Uses for GPIO in Ethernet Designs

### Potential Modifications (not in current design):

**LEDs** could show:
- Link status (LED ON = 10G link up)
- Traffic activity (LED blinking = packets flowing)
- Error indicators (LED red = CRC errors)
- Port status (one LED per SFP+ port)

**Switches** could control:
- Loopback enable/disable
- Speed selection (10G vs 1G)
- Flow control enable
- Test mode selection

**Buttons** could trigger:
- Link reset/re-negotiation
- Statistics counter clear
- Test packet generation
- Loopback mode toggle

---

## Modifying the Design to Use Buttons

If you want to add button functionality, modify `fpga_core.sv`:

```verilog
// Example: Use BTN-C to reset statistics counters
// Example: Use BTN-U/BTN-D to control loopback mode
// Example: Use LEDs to show link status instead of switches

// Current (simple):
assign led = sw;

// Proposed (show link status):
assign led[0] = sfp_rx_status[0];  // Port 0 link
assign led[1] = sfp_rx_status[1];  // Port 1 link
assign led[2] = sw[2];              // Unused
assign led[3] = sw[3];              // Unused
// ... etc

// Proposed (use button to trigger action):
reg btn_c_prev;
always_ff @(posedge clk_125mhz) begin
    btn_c_prev <= btnc;
    if (btnc && !btn_c_prev) begin
        // Rising edge detected - do something
        // e.g., trigger packet transmission
    end
end
```

---

## UART Port (for XFCP control)

**Location**: USB connector labeled "UART" or shares the main USB port
**Chip**: CP2108 quad UART (channel 2 is used)
**Baud rate**: 2 Mbaud (configured in design)
**Device**: Appears as `/dev/ttyUSB*` on Linux

**Connection**:
- Connect USB cable from computer to ZCU106 USB UART port
- Check `dmesg | grep tty` to find device (usually /dev/ttyUSB0-3)
- Use XFCP Python library to read statistics

---

## Summary

| Component | Quantity | Location | Current Function |
|-----------|----------|----------|------------------|
| LEDs | 8 | Top center | Mirror DIP switches |
| DIP Switches | 8 | Lower left | User input → LEDs |
| Push Buttons | 5 | Center | Debounced but unused |
| Reset Button | 1 | Lower right | System reset |
| UART | 1 | USB port | XFCP control @ 2 Mbaud |

**Quick verification**: 
1. Flip a switch → corresponding LED changes
2. All switches OFF → all LEDs OFF
3. All switches ON → all LEDs ON

This confirms the FPGA is programmed and running correctly!
