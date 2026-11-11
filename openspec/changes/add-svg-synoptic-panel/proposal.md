# Proposal

## Why

`MAXI_synoptic.svg` already contains the layout of the MAXI synoptic panel: hardware shapes, value slots,
plot slots and state assets. Nothing connects it to the control system yet. We need a PyDM panel that
renders this SVG and shows live Tango values on it, so operators see the MAXI state at a glance.
Connections must be configurable without touching code, so the same panel can follow changes in device
names.

## What Changes

- New PyDM display that renders `MAXI_synoptic.svg` as its background and scales it to the window, keeping
  its aspect ratio.
- New YAML configuration file with four sections:
  - `defaults`: `tango_host`, `tango_poll_period` (seconds, mapped to `PYDM_TANGO_POLL_PERIOD`) and
    `max_redraw_rate` (per second, for all plots).
  - `values`: SVG element id → Tango `source`, optional printf `format` that overrides the Tango format.
  - `plots`: SVG element id → Tango `source`, `refresh_period`, optional `log_y`, `time_span` and `y_range`.
  - `extra_channels`: name → Tango address, used only by the color and state rules.
- `PyDMLabel` widgets overlaid on the configured value slots, and `PyDMTimePlot` widgets overlaid on the
  configured plot slots. Slot bounds include SVG transforms.
- A Qt style sheet `maxi_synoptic.qss` with the font size and color of the values. Fonts do not scale:
  the panel is intended for a fixed window size.
- `DATETIME_value` shows the local date and time. It is not configured in the YAML.
- Color rules written in Python, which set the fill color of an SVG element from a channel value:
  - `MAXICHAMBER`: green for pressure ≤ 5e-6, yellow for ≤ 700, gray above.
  - `DETECTOR`: blue for temperature ≤ 15, gray above.
  - Unknown values show as gray with purple hatching.
- State rules written in Python, which show exactly one SVG asset per value:
  - `VALVE_OPEN`, `VALVE_CLOSED` and `VALVE_UNKNOWN`.
  - `SHUTTER_OPEN`, `SHUTTER_CLOSED` and `SHUTTER_UNKNOWN`.
  - Both use boolean attributes.
- Startup validation of the YAML and of all referenced SVG ids. Errors stop the panel from starting;
  inconsistencies log warnings.
- New PyTango simulator device `maxi/sim/1` that runs without a Tango database. It has writable
  attributes for every slot and rule channel, commands that set INVALID quality, and an optional drift
  mode. A `maxi_synoptic_sim.yaml` connects the panel to it, for tests and demos without the real
  control system.

## Capabilities

### New Capabilities
- `synoptic-config`: The YAML configuration format: its sections, keys, defaults, how Tango addresses are
  resolved, and how the configuration is validated against the SVG at startup.
- `synoptic-display`: Rendering the SVG and scaling it to the window, overlaying value labels and time
  plots on the configured slots, and the local clock.
- `synoptic-rules`: Color rules and state rules that change SVG elements from channel values, including
  how unknown values are shown and how rule targets and channels are validated.
- `maxi-simulator`: A Tango device that simulates the MAXI attributes, their quality and their changes
  over time, plus the panel configuration that uses it.

### Modified Capabilities
<!-- none: no existing specs -->

## Impact

- New Python code in this repository: the display module, config loader and validator, SVG
  widget, and the rule framework with the MAXI rules.
- New `maxi_synoptic.yaml` example configuration. The device names in it are placeholders until the
  real ones are known.
- New `sim/maxi_sim.py` simulator device and `maxi_synoptic_sim.yaml`.
- `MAXI_synoptic.svg`: not changed by this work. The "no transforms" rule in its header comment is no
  longer needed; the conventions are documented in `README.md`.
- Dependencies: PyDM with the Tango data plugin (`../pydm`), PyTango, Qt 5.15 / PyQt5 with QtSvg, and
  PyYAML.

## Assumptions (to be confirmed)

- The panel is launched as a PyDM Python display (`pydm maxi_synoptic.py`). By default it reads
  `maxi_synoptic.yaml` next to the display file. A PyDM macro `config` can name another file.
- A `source` without `tango://` gets `tango://` plus `defaults.tango_host` (if set) put in front of it. A
  `source` that already starts with `tango://` is used as is.
- The panel is read-only. No widget writes to Tango.
- Changed SVG elements are re-rendered at most every 100 ms, so bursts of updates are combined.
- "Unknown" means any of: disconnected, INVALID quality, NaN, a value of the wrong type, or no value
  received yet.
- `time_span` defaults to 600 s. PyDM's own default of 5 s is too short for vacuum trends.
- `DATETIME_value` shows the local time as `YYYY-MM-DD HH:MM:SS`.
- The simulator listens on port 45678 by default. Its drift mode only needs to show every color and
  state; it doesn't need to be physically realistic.
- Thresholds compare raw values and ignore units. Bands are `value <= upper`, and the first match wins.

## Out of Scope

- Writing to Tango or any other control actions.
- Configuring color or state rules in YAML. They stay in Python.
- Unit checking or conversion.
- States other than booleans (e.g. `DevState`) for valves and shutters.
- Qt 6 support, and the SVG `<pattern>` element (hatching is drawn by Qt instead).
- PyDM Designer integration.
- Filling plots with history from an archiver. Plots start empty.
- Editing the SVG layout, apart from the header comment.
- Realistic physics in the simulator (pump-down curves, valve interlocks, delays).
- Running the simulator with a Tango database, or TangoTest.
