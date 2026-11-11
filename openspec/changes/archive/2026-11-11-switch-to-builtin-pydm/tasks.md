# Tasks

## 1. Assets from the drawing

- [x] 1.1 Remove `rx` from `DETECTOR` in `MAXI_synoptic_v2.svg`, so that it has square corners. Verify in Inkscape or with QSvgRenderer that its shape is the plain rectangle 84,452,236x200
- [x] 1.2 Add `tools/export_assets.py` (ported from the prototype's `build_ui.py` export part): writes `background.svg`, `foreground.svg`, one SVG per state drawing (cropped, `display:none` stripped, shutter beams removed from `BEAM_VALVE_OPEN`, top margin for state words) and one empty SVG per symbol into `src/maxi_synoptic/resources/assets/`, plus a JSON of each symbol's crop bounds. Verify by running it and opening every exported SVG offscreen with QSvgRenderer (all valid, state words inside the crop)
- [x] 1.3 Commit the exported assets and add `tests/test_assets.py`: re-run the export into a temporary directory and compare with the committed files. Verify that the test passes, and fails after changing a colour in the drawing without re-exporting
- [x] 1.4 Rewrite README "Editing the SVG": the drawing is still the source, run `tools/export_assets.py` after editing it, which ids the export needs, and that a moved slot must also be moved in Designer. Verify that the documented command runs as written

## 2. Panel in Qt Designer

- [x] 2.1 Create `src/maxi_synoptic/resources/maxi_synoptic.ui` from the prototype, with every channel written as `${<signal>}` (simulator attribute names) and the calc channel of the beam after the shutter using `${valve_open_calc}` and `${shutter_open_calc}`. Use the layer order of design decision 2, the formats of the old default YAML, and plots per synoptic-display. Verify that it opens in `pydm designer` without warnings
- [x] 2.2 Write `src/maxi_synoptic/resources/maxi_synoptic.qss`: theme, label INVALID/disconnected styles, hatched brush for chamber and detector at severities 3 and 4, and the symbol image mappings for severities 0, 3 and 4. Verify by loading the `.ui` offscreen with the style sheet and every macro pointing to a non-existent device: chamber and detector are hatched and all four symbols show their UNKNOWN drawings
- [x] 2.3 Add `tests/test_ui.py`: (a) each value label and plot in the `.ui` lies within 1 px of its slot's bounds in the drawing; (b) each symbol's geometry matches the crop bounds from 1.2; (b2) the chamber circle and detector rectangle match the geometry, outline colour and stroke width of `MAXICHAMBER` and `DETECTOR`; (c) each severity-0 mapping in the style sheet equals the symbol's `imageFiles` in the `.ui`; (d) the chamber and detector rules give green/yellow/gray and blue/gray at the limits of synoptic-rules (5e-6, 700, 15). Verify that all pass
- [x] 2.4 Document in the README how to change a format, a threshold or a plot setting in Qt Designer, replacing the YAML key descriptions. Verify each documented property name exists in the `.ui`

## 3. Configuration and command

- [x] 3.1 Add `resources/default.json` (placeholder addresses of the old `maxi_synoptic.yaml`, written in full with `tango://maxi-ctrl:10000/`) and `resources/sim.json` (simulator on port 45678, `#dbase=no`). Verify that both name exactly the macros used in the `.ui` (excluding `*_calc`)
- [x] 3.2 Rewrite `cli.py`: resolve `--config` (bundled name or path, per synoptic-config), load and check the JSON (every error together, missing and unused signals, invalid JSON with line), add the `*_calc` macros with `#` encoded, refuse `-m`/`--macro`, check the Tango plugin, and start PyDM with `-m`, `--stylesheet` and the installed `.ui`. Verify with `tests/test_cli.py` updated for every scenario of "Configuration selection", "Configuration check", "Unused signals warn", "Panel command" and "Tango plugin check"
- [x] 3.3 Update `tests/test_maxi_sim.py` and the simulator's helpers (`panel_config` and friends) so that `sim.json` is the simulator configuration. Verify that `sim.json` passes the command's check with no errors or warnings (maxi-simulator "Simulator configuration")
- [x] 3.4 Rewrite the README sections "Running the panel" and "Configuration": the JSON format, `--config`, `PYDM_TANGO_POLL_PERIOD`, and a migration note from YAML (the mapping in the removed requirements of synoptic-config). Verify that the commands in the README run against the simulator

## 4. Remove the framework

- [x] 4.1 Delete `display.py`, `maxi_rules.py`, `synoptic/` and `resources/maxi_synoptic*.yaml`, and their tests (`test_config.py`, `test_validation.py`, `test_rules.py`, `test_overlays.py`, `test_svg_view.py`, `test_poll_period.py`, `test_maxi_synoptic.py`, `fixture.svg`). Verify that `grep -r "maxi_synoptic.synoptic\|maxi_rules\|yaml" src tests` finds nothing except intended hits
- [x] 4.2 Update `pyproject.toml`: runtime dependencies `pydm` and `pytango` only, package data for `*.ui`, `*.qss`, `*.json` and `assets/*`. Update `tests/test_packaging.py` to expect the new resources and no YAML. Verify that the packaging test passes and `pip install .` in a fresh env without PyYAML starts `maxi-synoptic --config sim`
- [x] 4.3 Update the README "Layout of the code" table and the installation section (dependencies). Verify that every file named in the table exists

## 5. Integration

- [x] 5.1 Rewrite `tests/test_integration.py` against the simulator, through the installed `.ui`, style sheet and `sim`-style macros: values with units; chamber green/yellow/gray and detector blue/gray; valve, shutter and beam drawings for open/closed combinations; INVALID shutter (shutter UNKNOWN, beam behind it unchanged); simulator stopped (labels disconnected, chamber hatched, valve/shutter UNKNOWN, beam through the valve, dashed beam behind the shutter) and recovery after a restart. Verify that it passes offscreen
- [x] 5.2 Run the full test suite (`pytest tests`) and an offscreen demo check like the README's (simulator `--drift`, state recorded every 0.5 s for 70 s, screenshots). Update the README "Demo check" with the date and results. Verify that every colour and state of the synoptic-rules scenarios appears in the record

## Workflow follow-up

- After implementation, update the `## Purpose` of the main specs `synoptic-config`, `synoptic-display` and `synoptic-rules` (they still describe YAML, SVG ids and Python rules), then archive the change.
- Delete the prototype in `../synoptic-comparison/pydm_builtin_maxi/` or point to the package once the change is archived.
