# Tasks

## 1. Simulator and configurations: `valve_state` and differential pump stage drift

- [x] 1.1 In `sim.py`, replace `valve_open` (bool) with `valve_state` (int, initial 0). Add a valve drift cycle of 0 for 10 s, 2 for 3 s, 1 for 10 s and 2 for 3 s, and a logarithmic drift of `diff_vac_pressure` between 1e-8 and 1000 mbar over 50 s. Verify with updated `tests/test_maxi_sim.py`: attribute types, drifting attributes, every valve state appears in order with MOVING shortest, and every differential pump stage colour band appears.
- [x] 1.2 Rename `valve_open` to `valve_state` in `default.json` (placeholder address) and `sim.json`. Update `tests/test_cli.py` (missing-signal cases, `_calc` macros) and verify `pytest tests/test_cli.py tests/test_maxi_sim.py` passes.
- [x] 1.3 Update the README: the simulator section (`valve_state` values, drift), the configuration section (signal list), and a **BREAKING** note for `valve_open` → `valve_state`. Verify that the README examples use only existing attribute names (`grep valve_open README.md` finds only the migration note).

## 2. Differential pump stage colour

- [x] 2.1 Add `PyDMDrawingRectangle` `diffpump` to `maxi_synoptic.ui` (drawing 1540,434 236×236, widget 1537,431 241×241 per design decision 6, pen `#aab4bf` 2.5, gray brush, brush rule from design decision 6), between `detector` and `foreground`. Verify in `tests/test_ui.py` that its geometry covers `DIFFPUMP` and that the rule gives green/yellow/red/gray at 8e-9, 1e-7, 5e-7, 1e-2, 1013.
- [x] 2.2 Add `PyDMDrawingRectangle#diffpump` to the hatching selectors of `maxi_synoptic.qss` for severities 3 and 4. Leave `DIFFPUMP` out of the background in `tools/export_assets.py`, and re-export. Verify with `pytest tests/test_assets.py` and an integration test: `diff_vac_pressure` written to 5e-7 shows yellow, and `SetInvalid("diff_vac_pressure")` shows hatching inside the rectangle.
- [x] 2.3 Add the differential pump stage to the README's Designer table and to the id table of the SVG section. Verify that both tables name `diffpump` and `DIFFPUMP`.

## 3. Valve display

- [x] 3.1 Create `resources/valve.ui` with the parts, geometry, brush rules, `Visible` rules and the `?` label from design decision 3, all on `${ch}`. Verify in `tests/test_ui.py` that every rule expression gives the table of decision 3 for the values 0, 1, 2 and 5, and that every channel in `valve.ui` is `${ch}`.
- [x] 3.2 Add the valve rules to `maxi_synoptic.qss`: words and `?` (decision 5), and at severities 3/4 a gray body, transparent gates, transparent words and a visible `?` (decision 2). Verify in `tests/test_ui.py` that the style sheet sets no brush or pen for valve parts at severities 0 to 2.
- [x] 3.3 In `maxi_synoptic.ui`, replace the `PyDMSymbol` `valve` with a `PyDMEmbeddedDisplay` `valve` (geometry 1310,442 196×184, `filename` `valve.ui`, `macros` `{"ch": "${valve_state}"}`, no frame). Verify with an integration test against the simulator: values 0, 1, 2 give the body colour, gate and visible word of the spec, and the panel shows no pieces of earlier states.
- [x] 3.4 Integration test for the unknown valve: `SetInvalid("valve_state")` shows a gray body, `?`, no gate and no word, and `ClearInvalid` shows the state again. Extend the stopped-simulator test: after a disconnect the valve shows the unknown look. Verify that `pytest tests/test_integration.py` passes.

## 4. Shutter display

- [x] 4.1 Create `resources/shutter.ui` from design decision 4 (frame pen rule, three blade brush rules, words, `?`), all on `${ch}`. Verify in `tests/test_ui.py` that the rules give the open and closed looks for True and False.
- [x] 4.2 Add the shutter rules to `maxi_synoptic.qss` (words, `?`, and at severities 3/4 a gray frame pen and transparent blades). Replace the `PyDMSymbol` `shutter` with a `PyDMEmbeddedDisplay` `shutter` (1094,432 128×214, `{"ch": "${shutter_open}"}`). Verify with integration tests: open/closed looks, INVALID and disconnect show the unknown look, and recovery after both.

## 5. Remove the reactive beam and the state images

- [x] 5.1 Remove the `PyDMSymbol`s `beam_valve` and `beam_shutter` and their calc channel from `maxi_synoptic.ui`, and all `PyDMSymbol` rules from `maxi_synoptic.qss`. Verify that `grep -c PyDMSymbol` finds no match in either file, and that `maxi-synoptic --config sim` starts with no warnings.
- [x] 5.2 Delete `layer_states` and `layer_beam` from `MAXI_synoptic_v2.svg`. Remove the symbol export from `tools/export_assets.py` (decision 7), delete the state images, the `*_none.svg` files and `symbols.json`, and re-export. Verify that `assets/` holds only `background.svg` and `foreground.svg`, that `pytest tests/test_assets.py` passes, and that a screenshot shows the dashed beam path and the arrow.
- [x] 5.3 Remove the symbol and crop tests from `tests/test_ui.py` and the beam tests from `tests/test_integration.py`. Update the packaging test to expect `valve.ui` and `shutter.ui` in the wheel. Verify with `pytest tests/test_ui.py tests/test_packaging.py`.
- [x] 5.4 Update the README: the Designer table (valve and shutter: edit `valve.ui`/`shutter.ui`, move the embedded display), the SVG section (no state layers and no symbol crops), the code-layout table, and remove the `PyDMSymbol` repaint requirement from Installation. Verify with `grep -n "PyDMSymbol\|symbols.json\|BEAM_VALVE\|BEAM_SHUTTER" README.md`, which finds no match.

## 6. Integration check

- [x] 6.1 Run `pytest tests` in the `maxi-synoptic` environment and verify that it passes.
- [x] 6.2 Demo check: run `maxi-synoptic-sim --drift` and the panel with `--config sim` offscreen for about 60 s, and record the states. Verify that the valve shows CLOSED, MOVING and OPEN, the shutter OPEN and CLOSED, and `DIFFPUMP` all four colours. After the simulator stops, verify that valve and shutter show `?` and the chamber, detector and differential pump stage are hatched. Update the README's demo-check section with the result.
- [x] 6.3 Open `maxi_synoptic.ui` in Qt Designer with the PyDM plugins, and check that the valve and the shutter appear as one widget each and can be moved. Note in the README if Designer does not draw their content.
