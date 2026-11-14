# Proposal

## Why

The valve, the shutter and the beam are state drawings in Inkscape. They are exported as one SVG per
state and shown by `PyDMSymbol` widgets, whose crops must match `symbols.json`. Their image mapping
is repeated in the style sheet. Moving or reshaping them means editing the drawing, re-exporting
and fixing the widget geometry. The valve now also needs a third state (MOVING, between its two end
switches), which would mean more exported images. Drawing these elements with PyDM's own drawing
widgets makes them editable in Qt Designer and removes the export of state drawings. The drawing
stays the static background.

## What Changes

- The valve and the shutter are each drawn by their own Designer file, `valve.ui` and `shutter.ui`,
  made of PyDM drawing widgets and labels. The panel embeds each one with `PyDMEmbeddedDisplay` and
  passes its channel as a macro. They are moved and resized in Qt Designer.
- **BREAKING** The valve signal `valve_open` (boolean) is replaced by `valve_state` (integer):
  0 = CLOSED, 1 = OPEN, 2 = MOVING. Configurations must rename the signal and point it to an integer
  attribute. The simulator's attribute changes the same way.
- The valve gets a MOVING look: an amber body with the gate closed halfway, and the word `MOVING`.
- The state words (OPEN, CLOSED, MOVING) are plain text in one neutral colour. They are no longer
  coloured by state.
- **BREAKING** The beam is no longer drawn from the valve and shutter states. Only the static dashed
  beam path and the direction arrow of the drawing remain. The solid beam, its stop marks and its
  unknown look are removed.
- The differential pump stage `DIFFPUMP` is coloured by its pressure `diff_vac_pressure`: green for <= 1e-7,
  yellow for <= 1e-6, red for <= 700, gray above 700. An unknown pressure shows gray with purple
  hatching, as for the chamber.
- The simulator's drift mode cycles the differential pump stage pressure, so that all its colours appear, and
  moves the valve through CLOSED, MOVING, OPEN, MOVING.
- Removed: the `PyDMSymbol` widgets, the state and beam images, `symbols.json`, the state and beam
  layers of the drawing, the symbol export of `tools/export_assets.py`, and the image rules in
  `maxi_synoptic.qss`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `synoptic-rules`: valve and shutter states are drawn by PyDM widgets, not SVG assets. The valve
  has three states from an integer. The beam is static, and its state rules and unknown rules are
  removed. A new colour rule is added for the differential pump stage.
- `synoptic-display`: the valve and the shutter are reusable embedded displays, placed in Designer.
- `synoptic-config`: the signal `valve_open` becomes `valve_state`.
- `maxi-simulator`: `valve_state` is an integer attribute. Drift mode cycles the valve through its
  three states and cycles the differential pump stage pressure.
- `synoptic-packaging`: the installed resources include `valve.ui` and `shutter.ui` instead of the
  state images.

## Impact

- **Resources:** new `valve.ui` and `shutter.ui`. `maxi_synoptic.ui` loses four `PyDMSymbol`s and
  gains two embedded displays and the `diffpump` rectangle. `maxi_synoptic.qss` loses the image
  rules and gains rules for the valve, the shutter and the differential pump stage. The state and beam images
  and `symbols.json` are removed from `assets/`.
- **Drawing:** the layers `layer_states` and `layer_beam` are removed from `MAXI_synoptic_v2.svg`.
  `DIFFPUMP` is no longer exported into the background, as for `MAXICHAMBER` and `DETECTOR`.
- **Code:** `tools/export_assets.py` exports only the background and the foreground. `sim.py` gets
  the integer valve and the differential pump stage drift. `cli.py` is unchanged: it still finds the used
  signals in `maxi_synoptic.ui`.
- **Configurations:** `default.json` and `sim.json` rename `valve_open` to `valve_state`. An
  existing user configuration fails the start-up check until it is renamed.
- **Tests:** the symbol and crop checks in `test_ui.py` and the beam checks in `test_integration.py`
  are removed. New checks cover the valve's three states, the shutter, the unknown looks and the
  differential pump stage colours.
- **Dependencies:** `disconnectedText`/`displayLabelText` of `PyDMLabel` need PyDM 1.29 or newer;
  the `tango_plugin` fork already has them. PyDM no longer needs the `PyDMSymbol` repaint fix.
- **README:** the Designer table, the SVG-editing section and the migration notes are updated.

## Out of scope

- Any reactive beam drawing (solid beam, stop marks, beam unknown look).
- Coloured state words.
- Changing the shutter's signal: `shutter_open` stays a boolean.
- More valves or shutters than the one each the panel has today, although the embedded displays
  would make that easy.
- Moving or reshaping the static drawing: pipes, chambers and the beam path stay in Inkscape.
- The INVALID-quality gap of the old beam: it disappears together with the beam.
- Write controls: the panel stays read-only.

## Assumptions (please confirm)

1. **Unknown look of the valve and the shutter:** gray body (valve) or gray frame (shutter), no gate
   or blades, a large `?` in the body, and no state word. This applies when the channel is disconnected, the quality is INVALID,
   or no value has arrived yet. It is the old look without the small `?` above the body.
2. **Other valve values:** an integer other than 0, 1 or 2 shows the unknown look. The style sheet
   only sees the quality, so the rules draw it: a gray body, no gate, no word, and a second `?` label
   that a `Visible` rule shows.
3. **MOVING look:** amber body (`#d6a544`), with the upper half of the gate closed and the lower
   half open.
4. **Differential pump stage colours:** green `#4fae7b`, yellow `#d6a544`, red `#cf5b5b`, gray `#6b7480`,
   with the chamber's outline. A value equal to a limit takes the lower band (1e-7 is green).
5. **Stacking:** the valve and the shutter sit below the foreground image, so the dashed beam path
   is drawn on top of them. In their area the foreground draws nothing else.
6. **Simulator drift:** the valve is CLOSED for 10 s, MOVING for 3 s, OPEN for 10 s and MOVING for
   3 s. The differential pump stage pressure cycles logarithmically between 1e-8 and 1000 mbar in 50 s.
