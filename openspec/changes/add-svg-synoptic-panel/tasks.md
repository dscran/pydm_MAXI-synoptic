# Tasks

## 1. Setup

- [x] 1.1 Create the module layout from design D1 (`synoptic/` package, `tests/`, `tests/conftest.py` setting `QT_QPA_PLATFORM=offscreen`). Document in `README.md` how to run the panel and the tests with the `maxi-synoptic` conda environment (the `../pydm` pixi environment was not usable), with `../pydm` on `PYTHONPATH`. Verify that `pytest tests` runs and collects no tests yet without errors.

## 2. Configuration loading (synoptic-config)

- [x] 2.1 Implement YAML loading and the schema for `defaults`, `values`, `plots` and `extra_channels` in `synoptic/config.py`: required and optional keys, the `time_span` default of 600 s and the `log_y` default of false, and errors that are collected rather than raised one at a time. Verify with unit tests covering unknown top-level and entry keys, a missing `source`, a non-positive `refresh_period`/`time_span`/`tango_poll_period`, and a missing section.
- [x] 2.2 Implement Tango address resolution (a full `tango://` address is used as is; otherwise `tango_host` is prefixed when set). Verify with unit tests for the three scenarios in the spec.
- [x] 2.3 Implement printf `format` parsing into display format and precision (design D5), rejecting a format without `%`. Verify with unit tests for `%.2e`, `%6.3f`, `%d`, `%s` and the invalid `6.3f`.
- [x] 2.4 Report YAML syntax errors with line and column, plus the quoting hint for an unquoted `%`. Verify with a unit test loading `format: %6.3f`.
- [x] 2.5 Implement the config-file lookup (`maxi_synoptic.yaml` next to the display, or the `config` macro resolved against the display directory). Verify with unit tests for both cases.

## 3. SVG view (synoptic-display)

- [x] 3.1 Implement the SVG DOM wrapper in `synoptic/svg_view.py`: parse with namespaces kept, list the ids, set/get `fill` and `display` in `style`, and serialize. Verify with unit tests that a round trip keeps the Inkscape attributes, and that changing the style touches only the targeted entry.
- [x] 3.2 Implement the SVG widget: render from the DOM, scale to fit, center, fill the leftover area with the `BACKGROUND` fill, and map SVG coordinates to widget coordinates with element bounds through `transformForElement` (design D4). Verify with pytest-qt tests on a fixture SVG with nested `translate()` transforms: a 1000x1000 window gives a centered 1000x562.5 drawing, and the mapped bounds of a transformed element match its expected pixel rectangle.
- [x] 3.3 Implement repaint batching with a 100 ms single-shot timer (design D3). Verify with a pytest-qt test that 50 DOM changes within 100 ms lead to one re-render showing the last state.
- [x] 3.4 Implement shape-exact hatching for a set of element ids (design D9), with a cache that is rebuilt on resize and when the set changes. Verify with a pytest-qt pixel test on a fixture circle: purple and gray pixels inside the circle, none outside its outline, and correct placement for a transformed element.

## 4. Overlays (synoptic-display)

- [x] 4.1 Implement the value-label overlays in `synoptic/overlays.py` (read-only `PyDMLabel`, alarm-sensitive border, unit shown, format override per design D5, font from the style sheet, see 10.2). Verify with pytest-qt tests that a label for `MAXI_VAC_pressure_value` covers the bounds of its slot at scale 1, that it is at half size after resizing to 960x540, and that `%.2e` shows 0.000012345 as `1.23e-05`.
- [x] 4.2 Implement the time-plot overlays (fixed-rate mode, `updateInterval`, `timeSpan`, log y-axis, white background; design D6). Verify with pytest-qt tests that the widget properties match a plot entry with and without the optional keys, and that the plot covers its slot bounds.
- [x] 4.3 Implement the local clock over `DATETIME_value` (`YYYY-MM-DD HH:MM:SS`, 1 s timer). Verify with a pytest-qt test that the text matches the format and changes after one second.

## 5. Rule framework and MAXI rules (synoptic-rules)

- [x] 5.1 Implement the rule framework in `synoptic/rules.py`: the `color_rule`/`state_rule` decorators, the registry, the `bands()` helper, channel binding through `PyDMChannel` (connection, value and severity), the unknown cases (design D8), state rules accepting `bool`/0/1, the initial unknown look, and a check that a callback's return value is a declared asset. Verify with unit tests feeding values to the slots directly: disconnected, INVALID severity, NaN, a wrong type, no value yet, ALARM severity still known, int 1 treated as True, int 2 as unknown, and `bands()` at an exact limit.
- [x] 5.2 Connect the rules to the SVG widget: color rules set `fill`, and unknown color rules add their targets to the hatched set; state rules show one asset and hide the others; every rule is applied as unknown before any channel connects. Verify with pytest-qt tests on the real `MAXI_synoptic.svg`: after startup only the `*_UNKNOWN` assets are visible, even if the file was saved with `VALVE_OPEN` visible.
- [x] 5.3 Implement the MAXI rules in `maxi_rules.py` (`MAXICHAMBER`, `DETECTOR`, valve and shutter, with the colors from design D10). Verify with unit tests for every scenario in the `synoptic-rules` spec (3e-7, 1e-3, exactly 700, 1013; -40 and 22; valve True/disconnected; shutter False/INVALID).

## 6. Validation and poll period (synoptic-config, synoptic-rules)

- [x] 6.1 Implement `synoptic/validation.py`: errors for an id not in the SVG ("no SVG element with id '<id>'"), an id in both `values` and `plots`, a rule target not in the SVG, and a rule channel not in `extra_channels`; warnings for an unconfigured `*_value`/`*_plot` element (except `DATETIME_value`) and an unused extra channel. Verify with unit tests for each case, and one test that several errors are reported together.
- [x] 6.2 Implement the poll-period handling (design D7): set `PYDM_TANGO_POLL_PERIOD` from the YAML only when it is not set, log which value is used, and warn when `"tango"` is already in `pydm.data_plugins.plugin_modules`. Verify with unit tests using `monkeypatch` for the environment variable and the plugin registry.

## 7. Display entry point and configuration

- [x] 7.1 Implement the `maxi_synoptic.py` PyDM Display, wiring everything in the order from design D1 and raising one `ConfigError` that lists all errors. Verify with a pytest-qt test that a valid config builds the display with the expected number of labels, plots and rules, and that an invalid config raises `ConfigError` listing every error.
- [x] 7.2 Write `maxi_synoptic.yaml` with entries for all value and plot slots in the SVG, the extra channels for the four rules (placeholder device names, clearly marked), and comments explaining each key. Verify that the validation of 6.1 passes with no errors and no warnings against `MAXI_synoptic.svg`.
- [x] 7.3 Document the SVG conventions in `README.md` ("Editing the SVG"): the ids the panel uses, the state asset convention (`<X>_OPEN`/`<X>_CLOSED`/`<X>_UNKNOWN`), and that transforms are allowed. The header comment of `MAXI_synoptic.svg` is not read by the panel and is left to whoever edits the file in Inkscape. Verify that an SVG saved by Inkscape loads and that the 7.1 test passes.

## 8. Simulator device (maxi-simulator)

- [x] 8.1 Implement `MaxiSim` in `sim/maxi_sim.py` with writable attributes for every slot and rule channel (types, units, formats), and change events pushed on write (design D13). Verify in the integration test (9.1), which is the only test that starts a device server: the pressure attribute has unit `mbar` and format `%.2e`, the valve attribute is a `DevBoolean`, and written values reach the panel through change events.
- [x] 8.2 Implement `SetInvalid`/`ClearInvalid`. Verify in the integration test (9.1) that INVALID quality reaches the panel and is cleared again, and that an unknown name raises a Tango error naming it.
- [x] 8.3 Implement drift mode (the `Drift` property, the 0.5 s loop, the ranges and periods from design D13). Verify with a unit test of the waveform functions that one cycle covers <= 5e-6, the range between 5e-6 and 700, and > 700, and that only the four drifting attributes get drift values. Drift on the running device is checked in the demo (9.2).
- [x] 8.4 Implement the command-line entry point (`--port`, default 45678, and `--drift`) using `DeviceTestContext` without a database. Document starting the simulator and the panel on it in `README.md`. Verify by running the documented commands and reading one attribute with `tango.DeviceProxy("tango://localhost:45678/maxi/sim/1#dbase=no")`.
- [x] 8.5 Write `maxi_synoptic_sim.yaml`, connecting every value slot, plot and rule channel to the simulator. Verify that the 6.1 validation passes with no errors and no warnings against `MAXI_synoptic.svg`.

## 9. Integration check

- [x] 9.1 Add a pytest-qt integration test that starts `MaxiSim` in a `DeviceTestContext` and the panel with a config generated for the test port. Check that:
  - a value label shows a written value;
  - a plot grows a curve;
  - `MAXICHAMBER` turns green, yellow and gray for written pressures;
  - `SetInvalid` hatches `MAXICHAMBER` and shows `SHUTTER_UNKNOWN`;
  - writing the valve attribute switches between `VALVE_OPEN` and `VALVE_CLOSED`;
  - stopping the device turns every rule unknown.

  Verify that the test passes.
- [x] 9.2 Manual demo check: start the simulator with `--drift` and the panel with `config=maxi_synoptic_sim.yaml`. Verify by watching every chamber and detector color, both valve and shutter states, and the hatching after stopping the simulator. Note the result in `README.md`.

## 10. Redraw rate and style sheet

- [x] 10.1 Add `defaults.max_redraw_rate` (whole number > 0) to the schema and pass it to `maxRedrawRate` of every plot. Document it in `maxi_synoptic.yaml`. Verify with unit tests for valid and invalid values, and a pytest-qt test that the plots of the display get the configured rate.
- [x] 10.2 Add `maxi_synoptic.qss` with the font size and color of the value labels and the clock, load it in the display, and remove the font scaling and the colors from the code. Verify with pytest-qt tests that a label has the font size of the style sheet, keeps it after resizing the window, and has the dark text color under a dark desktop palette.

## 11. Layout version 2

- [x] 11.1 Draw `MAXI_synoptic_v2.svg` (design D15) with the same ids, and load it in the display. Leave `MAXI_synoptic.svg` in place. Update the rule colors, the hatching and `maxi_synoptic.qss` to the new palette. Verify that both YAML files validate against it without errors or warnings, and by screenshots of the panel on the simulator: values, every state of valve and shutter, and the hatched unknown look.
- [x] 11.2 Make a plot take the fill of its SVG slot as background, with matching light or dark axes. Verify with pytest-qt tests for a white and a dark slot.

## 12. Fixed y-axis

- [x] 12.1 Add the optional plot key `y_range: [lowest, highest]` to the schema and apply it to the plot's y-axis (design D6). Set it for the pressure plots in both YAML files. Verify with unit tests for valid and invalid ranges, including the `log_y` rule and numbers that YAML reads as text, with pytest-qt tests that a linear and a logarithmic plot show the fixed range and keep it for values outside of it, and with a screenshot of the panel on the simulator.
