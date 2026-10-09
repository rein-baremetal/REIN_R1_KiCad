# REIN_R1 Hardware Design (KiCad 8.0+)
<img width="935" height="1320" alt="REIN_R1_placement_preview" src="https://github.com/user-attachments/assets/b3f194d9-21f2-45cf-b91e-56f4fdc26fa6" />

Welcome to the **REIN_R1** open-source PCB hardware project, part of the [REIN Baremetal](https://github.com/rein-baremetal) organization!

REIN_R1 is a multi-controller embedded development board built specifically for baremetal development, dual-architecture real-time control, and high-reliability embedded system experiments.

---

## What Makes REIN_R1 Stand Out?

Unlike standard single-SoC maker boards or basic evaluation kits, REIN_R1 combines high-performance coprocessing, rich peripheral interfacing, and power flexibility on a single compact 4-layer PCB:

* **Dual Microcontroller Co-Processing Architecture:** Integrates dual MCUs on-board to allow simultaneous execution of dedicated real-time control loops alongside higher-level communication and application tasks.
* **On-Board High-Speed QSPI Storage:** Dedicated QSPI flash interface configured for fast memory-mapped execution (XIP) and rapid firmware assets retrieval.
* **Integrated Hardware USB Hub:** Built-in multi-port USB hub logic eliminates external debug adapters, handling simultaneous programming, serial telemetry, and peripheral expansion over a single USB-C connection.
* **Robust Multi-Rail Power Management:** Features protected power input, integrated buck regulation, dedicated low-noise analog power paths (`3V3_A`), and smart battery/line switching (`VSYS`, `VIN`, `VBAT`).
* **Flexible Expansion & Communication:** Exposes dedicated SPI, I2C, UART, ADC channels, and GPIO arrays directly mapped for fast baremetal driver development without hardware bottlenecks.

---

## Current PCB Status

- **Schematic (`REIN_R1.kicad_sch`):** 100% Complete & Verified
- **Footprints & Symbol Libraries:** Custom library included (`REIN.kicad_sym`, `REIN.pretty/`)
- **Component Placement (`REIN_R1.kicad_pcb`):** 100% Complete
- **Routing:** **In Progress (Help Needed!)**

We are seeking open-source collaborators, hardware engineers, and layout enthusiasts to help route the remaining traces and achieve a 100% routed board that passes KiCad DRC with zero errors.

---

## Technical Specifications & Constraints

- **Board Layers:** 4 Layers (`F.Cu`, `In1.Cu` - GND, `In2.Cu` - Power Fills, `B.Cu`)
- **Default Track Width:** 0.20 mm (8 mil)
- **Default Track Clearance:** 0.20 mm (8 mil)
- **Minimum SMD Clearance:** 0.05 mm
- **Via Drill/Size:** Standard 0.3 mm / 0.6 mm

### Critical Routing Guidelines
1. **USB Differential Pairs (`/USB_DM_*`, `/USB_DP_*`):** Keep trace lengths matched and route as 90 Ω differential pairs. Minimize layer changes.
2. **QSPI Lines (`/QSPI_SCLK_*`, `/QSPI_SD0_*` to `/QSPI_SD3_*`, `/QSPI_SS_*`):** Length-match bus signals where feasible between MCU and flash storage. Keep tracks direct.
3. **Oscillator Traces (`/XIN_*`, `/XOUT_*`):** Keep routes as short as possible and isolate with ground pour fills.
4. **Power & Ground (`/GND`, `/3V3`, `/5V`, `/VIN`, `/VSYS`):** Ensure `In1.Cu` and `In2.Cu` ground planes maintain continuous connectivity without creating starved thermal islands on power/GND pads. Recalculate filled zones (`Ctrl + B`) after routing.

---

## How to Collaborate & Route

You can participate using either **KiCad PCB Editor** or **Freerouting**:

### Option A: Interactive Routing in KiCad
1. Clone or fork this repository:
   ```bash
   git clone [https://github.com/rein-baremetal/REIN_R1_KiCad.git](https://github.com/rein-baremetal/REIN_R1_KiCad.git)
