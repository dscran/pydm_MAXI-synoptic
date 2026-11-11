# Proposal

## Why

The panel draws itself through ~925 lines of its own framework (SVG view, overlays, rule engine, YAML
schema and validation). A prototype built only from PyDM's built-in widgets, a Qt Designer file and a
style sheet (`../synoptic-comparison/pydm_builtin_maxi/`) showed the same values, trends, colours,
states and unknown looks. It needed no Python of its own, and used 13 % of a core instead of 35 % at
10 Hz. Switching to it removes most of the code we maintain, and makes the panel editable in Qt Designer.

## What Changes

- **BREAKING** The panel becomes a Qt Designer file `maxi_synoptic.ui` with stock PyDM widgets:
  PyDMLabel for values, PyDMTimePlot for trends, PyDMSymbol for valve, shutter and beam states,
  PyDMDrawingCircle/Rectangle with PyDM rules for the chamber and detector colours, and PyDMDrawingImage
  for the drawing. Placement and settings are edited in Designer, not in YAML.
- **BREAKING** The panel has a fixed size of 1920×1080. The drawing and the widgets no longer scale with
  the window.
- **BREAKING** Channel addresses become PyDM macros, one per signal (for example
  `${maxi_vac_pressure}`). `maxi-synoptic --config default|sim|<file>.json` loads a JSON file of macros
  and passes it to PyDM. The YAML files, their schema and their validation against the SVG are removed.
- The unknown looks (hatched chamber and detector, UNKNOWN drawings of valve, shutter and beam) come
  from the style sheet, keyed on the `alarmSeverity` property that PyDM sets for INVALID quality and
  for disconnected channels.
- The detector in the drawing gets square corners, so that the PyDM rectangle laid over it matches
  its shape exactly.
- The drawing `MAXI_synoptic_v2.svg` stays the source of the graphics. A development script exports from
  it the background, the foreground and one SVG per state drawing. The exported files are committed and
  installed. The script is not used at run time.
- **BREAKING** The local clock is removed; its slot `DATETIME_value` stays empty.
- The trend plots get fixed colours that suit the dark slots; they no longer take their colours from
  the slot.
- Removed code: `synoptic/svg_view.py`, `overlays.py`, `rules.py`, `config.py`, `validation.py`,
  `poll_period.py`, `display.py`, `maxi_rules.py` and their tests. The simulator and the two commands
  stay.
- The Tango plugin check moves from the display into the `maxi-synoptic` command.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `synoptic-display`: the display is a Designer file at a fixed 1920×1080. Overlays no longer follow
  SVG ids, transforms or resizing. Plot colours are fixed. The clock is removed.
- `synoptic-rules`: rules become PyDM widget rules and symbols in the `.ui`, and unknown looks come
  from the style sheet. `extra_channels`, Python rules, rule validation and the repaint-rate
  requirement are removed. The unknown state of the beam after the shutter is relaxed (see the
  assumptions).
- `synoptic-config`: the YAML configuration, its sections, address resolution, defaults and
  validation are replaced by JSON macro files with one channel address per signal.
- `synoptic-packaging`: the bundled resources change (`.ui`, assets, macro files instead of YAML),
  the runtime dependencies shrink to `pydm` and `pytango`, and the Tango plugin check runs in the
  command.
- `maxi-simulator`: the simulator configuration becomes the bundled macro file `sim`.

## Impact

- **Code:** most of `src/maxi_synoptic/synoptic/` and `display.py` / `maxi_rules.py` are deleted.
  `cli.py` gains macro-file loading and the plugin check. A development script for exporting assets
  is added.
- **Resources:** `maxi_synoptic.ui`, `maxi_synoptic.qss`, `assets/`, `macros/default.json` and
  `macros/sim.json` are installed. `maxi_synoptic.yaml` and `maxi_synoptic_sim.yaml` are removed.
- **Operators:** a fixed 1920×1080 window with no clock. Values,
  trends, colours and states are as before. A disconnected value shows PyDM's own disconnected look:
  a dashed border, with the channel address as its text.
- **Users of the configuration:** a YAML file must be rewritten as a JSON macro file. Typos in a
  channel are no longer reported at start-up; the affected widget shows as disconnected.
- **Dependencies:** `pyyaml`, `numpy` and `qtpy` are no longer direct dependencies (PyDM still brings
  the last two). PyDM with the Tango plugin (fork) is still required.
- **Tests:** the framework tests go. Integration tests load the `.ui` offscreen against the simulator.

## Out of scope

- Sub-panels (related displays), write controls, zoom, layers and scaling with the window.
- A clock of any kind, and any heartbeat indicator (of the panel or of the control system). A heartbeat
  can follow in its own change; the empty `DATETIME_value` slot is left for it.
- Changes to the simulator's attributes or behaviour, beyond its bundled configuration.
- Getting the Tango plugin merged upstream, Qt 6, and visual redesign of the drawing.

## Assumptions (please confirm)

1. **One macro per signal.** The `.ui` uses one macro per channel (about 25), filled from the JSON
   file. PyDM has no macro-file option, so the `maxi-synoptic` command reads the file and passes it as
   `-m`. A JSON file is enough; YAML is not kept for this.
2. **No configuration validation.** A missing macro or a wrong address is not reported at start-up;
   the widget shows PyDM's disconnected look. The command checks only that the JSON file is a flat
   mapping of strings, and that every macro used in the `.ui` is defined in it.
3. **The beam after the shutter is combined from the valve and the shutter by a `calc://` channel.**
   It shows the unknown drawing when either channel is disconnected. The calc plugin does not pass
   quality on, so while the shutter is INVALID (but connected), this beam segment keeps its last state;
   the shutter drawing itself still shows UNKNOWN.
4. **The overlay shapes match the drawing exactly.** The chamber is a circle and the detector a
   rectangle laid over the drawing; colours and hatching fill those shapes. PyDM's rectangle cannot
   round its corners, so the detector in the drawing gets square corners (`rx` removed). Then
   colours and hatching follow the element's exact shape, as today.
5. **The exported assets are committed**, so installing the package needs no export step.
