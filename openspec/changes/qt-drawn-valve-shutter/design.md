# Design

## Context

The panel is `maxi_synoptic.ui`: a background image, PyDM shapes for the chamber and the detector, a
foreground image, four `PyDMSymbol`s (valve, shutter, two beam segments) and the labels and plots.
The symbols show SVGs exported from `layer_states` and `layer_beam` of the drawing. The style sheet
sets their unknown images by `alarmSeverity`. See proposal.md for why this changes.

Two limits of PyDM decide the approach. The archived design `switch-to-builtin-pydm` already
recorded them:

- The rules engine skips a rule while any of its channels is disconnected, so a rule keeps its last
  result. Rules alone cannot show an unknown look.
- The style sheet sees `alarmSeverity` (3 INVALID, 4 disconnected or no value yet), but not the value.
  `qproperty-visible` is ignored. A `qproperty-*` value stays set after its selector stops matching.
  Plain style sheet properties such as `color` do not stay set.

The installed PyDM (fork `tango_plugin`, which includes PyDM 1.29) has `PyDMLabel.displayLabelText`.
With it, a label keeps its own text, even when disconnected, and still gets `alarmSeverity`.

## Goals / Non-Goals

**Goals:**
- Value drives the look through rules. Unknown drives the look through the style sheet. The two
  never set the same property in conflicting ways, so the look does not depend on which comes first.
- One `.ui` per device type. It can be used again with another channel, with no Python code.

**Non-Goals:**
- Pixel-exact copies of the old state drawings. The geometry is kept; antialiasing and text
  rendering may differ slightly.
- Designer-side validation of the embedded displays beyond what the tests check.

## Decisions

### 1. Valve and shutter as embedded displays with a `ch` macro
`valve.ui` and `shutter.ui` sit next to `maxi_synoptic.ui`. Every widget inside them uses the
channel `${ch}`. The panel has one `PyDMEmbeddedDisplay` per device, with `filename` set to
`valve.ui` and `macros` set to `{"ch": "${valve_state}"}`. PyDM fills the panel's macros into the
text of the `.ui` before it is loaded, so the embedded display gets the full address.
`maxi-synoptic` still finds `valve_state` and `shutter_open` in `maxi_synoptic.ui`, so the
configuration check does not change. The embedded displays have no frame and a transparent
background. They take the geometry of the old symbol crops (valve 1310,442 196×184, shutter
1094,432 128×214), so the drawings stay where they are now. They sit between the shapes and the
foreground image, so that the dashed beam path `BEAM_axis` is drawn on top of them; in their area the
foreground has nothing else.

*Alternative:* the primitives placed directly in `maxi_synoptic.ui`. Rejected: moving a valve
would mean selecting about eight widgets, and a second valve would mean copying all of their rules.
*Alternative:* a Python widget class. Rejected: it needs our own code and a Designer plugin, and the
panel has no widget code of its own.

### 2. Each property has one owner: a rule, or the style sheet at severity 3/4
- **Rule-driven** (from the value): body brush, gate and blade brushes, visibility of the state
  words.
- **Style sheet at severity 3/4** (unknown): gray body brush or frame pen, `transparent` brushes for
  gate and blades, `color: transparent` on the words, and a visible colour on the `?` label.
- The style sheet does not set brushes or pens at severity 0 to 2. Brushes that the unknown look
  sets with `qproperty-` stay set. When the value is known again, the next value runs the rules,
  which set them again. The chamber already relies on this, and the tests check it there.
- Words and `?` use `color`, which the style sheet resets itself.

Hidden parts are drawn with a transparent brush instead of being hidden, because the style sheet
cannot hide widgets, and a `Visible` rule keeps its last result while disconnected. Words use
`Visible` rules anyway: whatever their visibility, the unknown look makes their text transparent.

*Alternative:* a `calc://` channel that turns 0/1/2 into a word, shown by one label. Rejected: the
calc channel does not pass on INVALID quality, so the word would stay while the body shows unknown.
It also shows its address while disconnected.

### 3. Parts of the valve (`valve.ui`)
Coordinates are relative to the widget. The old drawing's offset (1310,442) is subtracted. They are
the drawn boxes: a part with a pen (`valve_body`, `shutter_frame`) has a widget larger by the pen width
on each side, as the chamber and the detector have; `valve_body` is 27,39 142x142.

```
  word labels (y 4..40): valve_word_closed / _open / _moving, one visible at a time
  +--------------------------------+  valve_body   draws 30,42 136x136, pen #aab4bf 3
  |      [ valve_gate_top    ]     |  68,45  60x30
  |      [ valve_gate_upper  ]     |  68,75  60x35
  |      [ valve_gate_lower  ]     |  68,110 60x35
  |      [ valve_gate_bottom ]     |  68,145 60x30
  |             ?                  |  valve_unknown, valve_out_of_range: labels over the body
  +--------------------------------+
```

| Value | body | top | upper | lower | bottom | word |
|---|---|---|---|---|---|---|
| 0 | red `#cf5b5b` | dark | dark | dark | dark | CLOSED |
| 1 | green `#4fae7b` | dark | clear | clear | dark | OPEN |
| 2 | amber `#d6a544` | dark | dark | clear | dark | MOVING |
| other | gray `#6b7480` | clear | clear | clear | clear | `?` in body (`valve_out_of_range`) |
| unknown (style sheet) | gray | clear | clear | clear | clear | `?` in body |

Dark is `#262b31`, clear is a transparent brush. Each part has one brush rule on `${ch}`, for
example for `valve_gate_upper`: `QColor('#262b31') if ch[0] in (0, 2) else QColor(0, 0, 0, 0)`.
The word labels have `displayLabelText` on, fixed text, `alarmSensitiveBorder` off, and a `Visible`
rule such as `ch[0] == 2`. `valve_out_of_range` is a second `?` at the place of `valve_unknown`, always
dark, with the `Visible` rule `ch[0] not in (0, 1, 2)`: an integer without a state looks unknown,
although its quality is valid. Its rule keeps its last result while disconnected, which only adds a
`?` where the unknown look shows one anyway.

### 4. Parts of the shutter (`shutter.ui`)
`shutter_frame` (dark fill, pen 4: blue `#4b8fc4` when closed, yellow `#f0c75e` when open, gray on
unknown), and three blades between y 482 and 632 of the drawing: `shutter_blade_top` 46,
`shutter_blade_mid` 58, `shutter_blade_bottom` 46. Closed: all three blue. Open: top and bottom
`#aab4bf`, mid clear. Words `OPEN`/`CLOSED` and `?` as for the valve. The pen colour has a rule,
and the unknown look sets `qproperty-penColor`, in the same way as the brushes.

### 5. Words in one neutral colour
`valve_word_*` and `shutter_word_*` get `color: #d3d9df; font-size: 22px; font-weight: bold;`
through selectors on their names. These selectors also replace the general `PyDMLabel` rules (30 px,
INVALID and disconnected borders). The `?` labels get 64 px, transparent at severities 0 to 2, and
at 3/4 a colour that stands out from what is behind them, as in the old UNKNOWN drawings: dark
`#262b31` on the gray valve body (a gray `?` would vanish there), gray `#6b7480` on the dark shutter
frame. `valve_out_of_range` is always dark `#262b31`; its rule decides whether it is shown.

### 6. Differential pump stage as a third coloured shape
`diffpump` is a `PyDMDrawingRectangle` that draws the box of `DIFFPUMP` (1540,434 236×236, pen
`#aab4bf` 2.5). PyDM insets a shape by its pen width on each side, so the widget would have to be
1537.5,431.5 241×241, which Qt geometry cannot hold. It is 1537,431 241×241 and draws at 1539.5,433.5
236×236, half a pixel from the drawing; `test_ui.py` allows one pixel. It sits with the chamber and the detector, between the background and the
foreground image. Its brush rule on `${diff_vac_pressure}`:
`QColor('#4fae7b') if ch[0] <= 1e-7 else (QColor('#d6a544') if ch[0] <= 1e-6 else (QColor('#cf5b5b') if ch[0] <= 700 else QColor('#6b7480')))`.
The existing hatching selector gets `PyDMDrawingRectangle#diffpump` for severities 3 and 4.
`tools/export_assets.py` leaves `DIFFPUMP` out of the background, as it does `MAXICHAMBER` and
`DETECTOR`. `DIFFPUMP` already has square corners.

### 7. Drawing and export
`layer_states` and `layer_beam` (the state groups and `BEAM_entry`) are deleted from
`MAXI_synoptic_v2.svg`. `BEAM_axis` and `BEAM_arrow` stay in the foreground. The export keeps
`split_layers` and drops `SYMBOLS`, `export_symbol`, `state_drawing`, `crop_of` and `symbols.json`.
`test_assets.py` then compares only `background.svg` and `foreground.svg`.

### 8. `_calc` macros stay
With the beam gone, no channel in the `.ui` uses `<signal>_calc` any more. The command keeps adding
these macros: they cost nothing, and a future `calc://` channel will need them. `cli.py` is not
changed.

### 9. Simulator
`valve_state` gets the initial value `0` (Python `int`, so `DevLong64`). Drift computes the valve
from a 26 s cycle: 0 for 10 s, 2 for 3 s, 1 for 10 s, 2 for 3 s. `diff_vac_pressure` follows the
same logarithmic triangle as the chamber, between 1e-8 and 1000 mbar in 50 s. `SetInvalid` and
`ClearInvalid` work on every attribute already.

## Risks / Trade-offs

- [A rule may not run again on reconnect if the value is unchanged] → The Tango plugin sends the
  current value on every connect, and the rules engine runs on it. An integration test disconnects
  and reconnects the simulator and checks that the valve shows the right state again, as the chamber
  test already does.
- [The style sheet may be polished before or after a rule sets a brush] → Decision 2 keeps the two
  apart: at severities 0 to 2 the style sheet sets no brush or pen. An integration test runs
  INVALID → VALID and disconnect → reconnect.
- [Embedded displays might not get the application style sheet, or might draw a frame] → The style
  sheet is set on the application, so it applies to all widgets. An integration test checks the
  unknown look inside the embedded valve. `frameShape` is `NoFrame`.
- [Qt Designer might not show the embedded content] → It only affects editing. If it happens, the
  README says to edit `valve.ui` itself and to place the frame by its geometry.
- [Each part of a valve has its own channel connection] → PyDM shares one connection per address,
  so the control system sees one client.
- [Word text looks slightly different from the exported SVG text] → Accepted (non-goal).

## Migration Plan

1. Operators rename `valve_open` to `valve_state` in their own configurations and point it to the
   integer attribute. Until they do, the start-up check names the missing signal.
2. `default.json` gets `valve_state` with a placeholder address, as for the other signals.
3. Rollback: check out the previous commit. The old images come back with it.
