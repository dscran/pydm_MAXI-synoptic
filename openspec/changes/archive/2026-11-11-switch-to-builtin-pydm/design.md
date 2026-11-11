# Design

## Context

See proposal.md for the motivation. Today `display.py` builds the panel at run time: `SvgView` renders
the drawing with QSvgRenderer and re-renders all of it on every rule change; `Overlays` places PyDM
widgets on SVG element ids; `rules.py` runs Python colour and state rules on `extra_channels`; and
`config.py` and `validation.py` load and check the YAML. `cli.py` turns `--config` into PyDM's `config`
macro.

A prototype of the target exists in `../synoptic-comparison/pydm_builtin_maxi/` (`build_ui.py`,
`maxi_synoptic.ui`, `maxi.qss`, `assets/`). It was tested offscreen against the simulator: values,
plots, colours, states, INVALID and disconnect looks, and recovery. The decisions below come from what
worked there, and from PyDM limits found on the way.

## Goals / Non-Goals

**Goals:**
- At run time, nothing but PyDM: the `.ui`, the style sheet and the images. The only custom code that
  stays is `cli.py`, which loads the configuration and starts PyDM, and the simulator.
- The drawing stays the single source of the graphics; the `.ui` is the single source of placement and
  widget settings.
- The committed images can be checked to be up to date with the drawing.

**Non-Goals:**
- Pixel identity with the current panel (see the proposal's assumptions for the known differences).
- Keeping the YAML format, or a converter from YAML to JSON (there are two configurations, both bundled).

## Decisions

### 1. The `.ui` is committed and maintained in Qt Designer
The `.ui` is created once by porting the prototype's `build_ui.py` (signals as macros, package
paths), and from then on edited in Designer. The generator is not kept.
*Alternative:* keep generating the `.ui` from a description in code. Rejected: that keeps a second
source of truth and a code generator to maintain, which is what this change removes.

### 2. Layers of the panel
From back to front: `background.svg` (background, hardware below the chamber, panels and legend); the
chamber circle and detector rectangle (PyDMDrawingCircle/Rectangle with brush rules, with the same
geometry, outline colour and stroke width as `MAXICHAMBER` and `DETECTOR`, so that they cover the
drawn elements exactly; the detector's corners are made square in the drawing for this); `foreground.svg`
(beam axis, diode, names, magnets, beam entry: everything the drawing puts above the chamber); the four
state symbols in the order of the drawing (valve, shutter, then the beam after the valve and the beam
after the shutter, so that the beam is drawn over an open valve or shutter); then labels and plots. The two images are full-canvas PyDMDrawingImage widgets. Without the foreground layer, the
coloured circle would cover the magnets and the beam axis.

### 3. Assets exported from the drawing by a development script
`tools/export_assets.py` (not installed) writes into the package's `resources/assets/`: the background
and foreground SVGs (subsets of the drawing's layers), one SVG per state drawing, cropped to the union
of its state group's bounds, and one empty SVG per symbol. The state drawings' inline `display:none`
is stripped, and the shutter beams are removed from the copy of `BEAM_VALVE_OPEN`. Qt reports no bounds
for `<text>`, so the crop adds a top margin for the state words. A test re-runs the export into a temporary directory and
compares it with the committed files, so a drawing edit without re-export fails the tests. The symbols'
widget geometry in the `.ui` must match the crop; the same test checks each symbol's geometry against
the bounds the export computed.

### 4. Unknown looks from the style sheet
PyDM's rules engine skips a rule while any of its channels is disconnected, so rules alone would
freeze, as in svgsynoptic2. Every PyDM widget with a channel has the property `alarmSeverity` (0 OK,
3 INVALID, 4 disconnected), and the style sheet selects on it:
- Chamber and detector: `qproperty-brush` with a repeating striped `qlineargradient` for severities 3
  and 4. When the value comes back, PyDM restores the brush and the rule sets the right colour.
- Symbols: `qproperty-imageFiles` maps every value to the UNKNOWN drawing for severities 3 and 4.
  Values set with `qproperty-` are not reset when the selector stops matching, so severity 0 needs its
  own rule with the normal mapping (the same mapping as in the `.ui`). `qproperty-visible` is ignored by
  Qt, so a hidden drawing is an empty image.
- Labels: INVALID colour and border.

*Alternative:* hide and show separate image widgets with Visible rules. Rejected because those rules
freeze on disconnect.

### 5. Beam after the shutter through a calc channel
That segment depends on the valve and the shutter. A `calc://` channel computes `0` (valve closed:
nothing), `1` (open beam) or `2` (stop mark). The calc channel disconnects when either input does, which
gives the UNKNOWN drawing through rule 4. It does not pass quality on, which causes the INVALID gap
accepted in the proposal (assumption 4).
*Alternative:* a symbol on the shutter channel plus a Visible rule on the valve. It handles shutter
INVALID, but on a valve disconnect the visibility freezes, possibly hiding the beam. That contradicts
"wrongly showing beam is the safer mistake", so it is rejected.

### 6. Configuration as PyDM macros, prepared by the command
The `.ui` uses `${<signal>}` for every channel; the signal names are the simulator's attribute names.
`maxi-synoptic` resolves `--config` (bundled `default`/`sim` or a path) and loads the JSON. It checks
the file against the set of macros used in the `.ui`, which it reads from the installed file, so there
is no second list of signals. It then calls PyDM with `-m <json>`, `--stylesheet <installed qss>` and
the installed `.ui`. Addresses with `#dbase=no` break the calc URL, which `urllib` cuts at `#`. For
the signals used inside calc channels (`valve_open`, `shutter_open`), the command therefore adds the
macros `<signal>_calc` with `#` encoded as `%23`.
*Alternative:* `TANGO_HOST`-style macros with device names in the `.ui`. Rejected: the simulator's
names differ from the real ones.

### 7. Tango plugin check in the command
With no Python display, the check runs in `cli.py` before PyDM starts, using `find_spec` as today.

## Risks / Trade-offs

- [Drawing and `.ui` drift apart: a slot moved in the drawing does not move its widget.] → The
  asset-export test checks the symbols. For labels and plots, a test compares each widget's geometry
  in the `.ui` with its slot's bounds in the drawing.
- [Typos in addresses are only visible as disconnected widgets.] → The command checks that every macro
  is defined. The disconnected look names the address in the label itself.
- [A coloured shape that does not match its drawn element leaves a sliver of the drawing's colour
  visible, or paints outside the element.] → A test compares the shapes' geometry with the elements.
- [The style sheet carries each symbol's image mapping a second time (for severity 0).] → A test
  checks that each severity-0 mapping in the style sheet equals the symbol's `imageFiles` in the `.ui`.
- [`qproperty-` behaviour of PyDM/Qt can change with versions.] → The integration test covers
  disconnect, INVALID and recovery against the simulator.
- [The fixed 1920×1080 size is unusable on smaller screens.] → Accepted (proposal); a scroll area is
  possible later without changing the specs.
- [Exit-time segfault seen at 10 Hz in the libtango teardown (comparison study).] → Not caused by
  this change; it may still appear in tests that stop the Qt application quickly. It is watched, not
  solved, here.

## Migration Plan

1. Land the change in one step: the YAML panel and the `.ui` panel are not run side by side.
2. Operators start the panel as before (`maxi-synoptic`, `--config sim`). A local YAML configuration
   must be rewritten as JSON (README section with the mapping from the removed requirements).
3. Rollback: install the previous version of the package; the configurations are not shared, so keep
   the YAML file until the new panel is accepted.
