# Design

## Context

See proposal.md for the motivation and specs/ for the required behavior. Constraints that shape the
approach:

- The repository holds only the SVGs so far, so all the code is new.
- **The runtime is Qt 5.15 / PyQt5.** QtSvg implements SVG Tiny 1.2, so it has no `<pattern>` support.
  `QSvgRenderer` also offers no API for changing an element after the file is loaded.
- **The Tango plugin (`../pydm`, `pydm/data_plugins/tango_plugin.py`)**:
  - It receives change events and falls back to polling. It reads `PYDM_TANGO_POLL_PERIOD` once, when its
    module is imported.
  - It sends `DevBoolean` and `DevState` as integers, with enum strings.
  - It maps quality to PyDM severity, with INVALID = 3.
- **PyDM loads data plugins lazily.** `plugin_for_address()` initializes them on the first connection,
  and the loaded plugins live in `pydm.data_plugins.plugin_modules`, keyed by protocol.
- **PyDM widgets:**
  - `PyDMTimePlot` defaults to a 5 s time span. It supports `UpdateMode.AtFixedRate` with an
    `updateInterval`, and a log scale per axis.
  - `PyDMLabel` formats with `displayFormat` (e.g. Exponential) plus `precision`.
- **The SVG (`MAXI_synoptic.svg`, 1920x1080 viewBox):**
  - The state assets carry `translate()` transforms.
  - The `BACKGROUND` element has fill `#2e3436`.
- **Environment.** The conda environment `maxi-synoptic` (see `README.md`) provides PyTango 10.3,
  PyQt 5.15, pyqtgraph, PyYAML, pytest and pytest-qt, with `../pydm` on `PYTHONPATH`. The `../pydm` pixi
  environment was planned first, but its copy on the development machine was not usable.

## Goals / Non-Goals

**Goals:**
- Keep the MAXI-specific parts (the rules and the YAML) separate from a reusable SVG-synoptic core, so
  that another panel can reuse the core.
- Make configuration loading and validation testable without Qt or Tango.
- Make rules testable by feeding values directly, with no Tango device.

**Non-Goals:**
- A general SVG editing library. The code changes only `fill` and `display` in an element's `style`.
- Packaging and installation. The panel runs from this repository.

## Decisions

### D1 Module layout
```
maxi_synoptic.py        PyDM Display entry point (pydm maxi_synoptic.py)
maxi_synoptic.yaml      configuration (placeholder device names)
maxi_rules.py           MAXI color and state rules
synoptic/
  config.py             YAML loading, schema, address resolution, printf parsing
  validation.py         checks against the SVG ids and rules; collects errors and warnings
  poll_period.py        applies the poll period to the Tango plugin (D7)
  svg_view.py           SVG widget: DOM, rendering, coordinate mapping, hatching, repaint timer
  overlays.py           builds the PyDMLabel, PyDMTimePlot and clock overlays
  rules.py              rule framework: decorators, unknown handling, channel binding
tests/
```
`config.py` and `validation.py` don't import Qt. `validation.py` gets the registered rules as an
argument, because `rules.py` imports PyDM. The display wires everything up in this order:
1. load the config;
2. apply the poll period;
3. load the SVG DOM;
4. validate, and stop on errors;
5. build the widget, overlays and rules.

### D2 SVG DOM in memory, re-rendered on change
The SVG is parsed with `xml.etree.ElementTree`, and the Inkscape/sodipodi namespaces are registered
so that serializing keeps them. Rules change the `fill` and `display` entries in an element's `style`
attribute. The changed DOM is then serialized and passed to `QSvgRenderer.load(QByteArray)`.
- *Alternative:* one `QGraphicsSvgItem` per element. Rejected: it still can't recolor elements, and
  it makes coordinate handling harder.
- *Alternative:* lxml. Rejected: the standard library is enough here.

### D3 Repaint batching
A rule change only marks the DOM as dirty and starts a single-shot 100 ms timer, if it is not already
running. When the timer fires, the DOM is re-rendered once and `update()` is called. This meets the
"at most 10 redraws per second, last value wins" requirement. Overlays are separate widgets, so their
redraws don't depend on this timer.

### D4 Coordinate mapping
The view uses `scale = min(w / 1920, h / 1080)` and centers the SVG. The leftover area is filled with
the fill color of `BACKGROUND`, or black if that element is missing. The slot rectangle in SVG units is
`renderer.transformForElement(id).mapRect(renderer.boundsOnElement(id))`, which is then mapped to widget
coordinates. `boundsOnElement` includes the stroke, so half the element's `stroke-width` is taken off
each side first; the slot is then the geometry of the element (e.g. 160x32 for the value slots). Every overlay is placed again in `resizeEvent`. Fonts do not scale, because the panel is made for a fixed
window size (see D14).

### D5 Value labels and printf formats
`config.py` parses `format` with `%[-+ #0]*\d*(?:\.(\d+))?([diouxXeEfFgGs])`:

| Conversion | `displayFormat` | Precision |
|---|---|---|
| `e`, `E` | Exponential | parsed |
| `f`, `F`, `g`, `G` | Decimal | parsed, default 6 |
| `d`, `i`, `o`, `u`, `x`, `X` | Decimal | 0 |
| `s` | String | — |

With a `format`, `precisionFromPV` is turned off. Without one, the label keeps PyDM's defaults, so the
Tango format reaches it as precision through the plugin. The width and flag fields are accepted but
ignored. The labels have `alarmSensitiveBorder` on. Their font size and color come from the style sheet (D14).

### D6 Time plots
Each plot is a `PyDMTimePlot` with one curve for its `source`, set up as follows:
- `UpdateMode.AtFixedRate`;
- `updateInterval = refresh_period`;
- `timeSpan = time_span` (600 s by default);
- the left axis in log mode when `log_y` is set;
- with `y_range`, auto-range of the y-axis turned off and its view range set to the two limits (their
  `log10` on a log axis). A fixed range also keeps the tick labels of a log axis readable, which overlap
  when the axis zooms in on a value that hardly changes;
- the background of its SVG slot, with light or dark axes and curve depending on how dark the slot is.

Fixed-rate mode is what makes values that rarely send events still draw a continuous curve.

### D7 Poll period
Before any channel is created, the display does the following:
- If `PYDM_TANGO_POLL_PERIOD` is set, it is kept, and the log says the YAML value is ignored.
- Otherwise it is set to `round(tango_poll_period * 1000)`.
- If `"tango"` is already in `pydm.data_plugins.plugin_modules`, a warning is logged, because the
  plugin module has already read the variable.

### D8 Rules as Python callbacks with a small framework
Rules are plain functions, registered with a decorator that declares the channel name and the SVG ids
the rule may change:

```python
@color_rule(channel="chamber_pressure", target="MAXICHAMBER")
def chamber(pressure):
    return bands(pressure, [(5e-6, GREEN), (700, YELLOW)], above=GRAY)

@state_rule(channel="valve_open", assets={"VALVE_OPEN", "VALVE_CLOSED"}, unknown="VALVE_UNKNOWN")
def valve(is_open):
    return "VALVE_OPEN" if is_open else "VALVE_CLOSED"
```

- **Channel binding.** The framework creates one `PyDMChannel` per rule, with connection, value and
  severity slots, and keeps the latest connection state, value and severity.
- **Unknown values.** These are decided by the framework, never by the callback, so a callback only
  ever receives usable values:
  - disconnected, severity 3, or no value yet;
  - for color rules: a value that is not a real number (bool excluded), or NaN;
  - for state rules: a value other than a bool, or the ints 0 and 1. The ints are accepted because the
    plugin sends `DevBoolean` as an int.
- **Callback results.**
  - A state callback must return one of its declared assets, otherwise the framework logs an error and
    shows the unknown asset.
  - A color callback returns a color string.
- **At startup**, every rule applies its unknown look before any channel connects.

`bands()` is a helper: the first `value <= upper` wins. Rules are registered in a module-level registry
that `validation.py` reads to check rule targets and channels.
- *Alternative:* declarative rule classes (`ColorRule(bands=...)`). Rejected because you asked for
  callbacks. The `bands()` helper keeps them just as short.

### D9 Hatching for unknown color rules
The DOM sets the element's fill to gray. After `renderer.render()`, `paintEvent` draws, for each hatched
element, a cached overlay image built like this:
1. Draw the SVG area inside the element's on-screen bounds twice, once with the element's fill set to
   black and once to white. The difference of the two images is the coverage of the visible fill, with
   antialiased edges.
2. Fill an image with a tiled brush of purple diagonal lines, and use the coverage as its alpha.

The coverage leaves out the element's stroke and everything drawn on top of the element. This matters
because the `MAXI vacuum` and `Detector` panels lie on top of `MAXICHAMBER` and `DETECTOR`: hatching
must not cover them.

The brush is a 12 px tile with 2 px lines. `Qt.BDiagPattern` was not used, because its lines are always
1 px wide.

The cache is rebuilt whenever the widget is resized, the hatched set changes, or the DOM is re-rendered
(another element might now cover the hatched one).

- *Alternative:* a `<pattern>` element in the SVG. Not rendered by Qt 5.
- *Alternative:* computing a `QPainterPath` from the SVG geometry. That means parsing paths ourselves.
- *Alternative:* render the element alone with `renderer.render(painter, id, bounds)` and use its alpha
  as the shape. Rejected: the hatching would also cover the panels on top of the element, and its stroke.

### D10 Colors
The colors come from the palette of `MAXI_synoptic_v2.svg`, which is muted so that the status colors
stand out on its dark background without being harsh:

| Use | Color |
|---|---|
| green | `#4fae7b` |
| yellow (amber) | `#d6a544` |
| blue | `#4b8fc4` |
| gray (known and unknown) | `#6b7480` |
| hatching | light purple `#c79bea`, 3 px lines |

They are constants in `maxi_rules.py` and `synoptic/rules.py`.

### D11 Validation output
`validation.py` returns lists of errors and warnings, as plain strings that name the id or key involved.
- **Warnings** are logged.
- **Errors** are all logged, then the display raises one `ConfigError` that lists them all, so PyDM shows
  the failure.
- **YAML syntax errors** report the line and column from `problem_mark`. When the problem text mentions
  `'%'`, the message adds that values starting with `%` must be quoted.
- **A missing id** gets the message "no SVG element with id '<id>'". Inkscape labels are not searched.

### D12 Clock
A 1 s `QTimer` updates a `ClockLabel` (a `QLabel`) over `DATETIME_value`, in the format
`YYYY-MM-DD HH:MM:SS`. Its style matches the dark slot: light text on `#232829`, set in the style sheet
(D14).

### D13 Simulator device
`sim/maxi_sim.py` defines a high-level PyTango `Device` `MaxiSim`. It serves the device `maxi/sim/1`,
with one attribute per slot or rule channel, named after the slot in snake case, e.g.
`maxi_vac_pressure`, `valve_open`.

**Attributes**
- All are `READ_WRITE`. A write stores the value and calls `push_change_event`.
- `set_change_event(name, True, False)` is enabled for every attribute, so the PyDM Tango plugin
  subscribes to events and does not poll.
- Units and formats are set as a real device would have them: `mbar` / `%.2e` for pressures, `°C` /
  `%.1f` for temperatures.

**Commands**
- `SetInvalid(name)` / `ClearInvalid(name)` keep a set of invalid attributes. Reads and events for those
  attributes use `AttrQuality.ATTR_INVALID`.

**Drift**
- With drift on, a `threading.Timer`-style loop, ticking every 0.5 s, runs inside the device and pushes
  events:
  - pressure moves along a log-scale triangle wave between 1e-7 and 1000 over 60 s;
  - temperature moves along a triangle wave between -40 and 30 over 40 s;
  - the valve toggles every 10 s, the shutter every 7 s.

**Running it**
- `python sim/maxi_sim.py [--port 45678] [--drift]` starts it in a `DeviceTestContext` with
  `device_name="maxi/sim/1"`, the given port, and the `Drift` device property. No Tango database is
  needed.
- Tests use the same class with `DeviceTestContext(MaxiSim, ..., process=True)`. That is how the
  plugin's own tests do it, and it keeps the device server in a separate process from the Tango client
  in the plugin.
- **Disconnects** are simulated by leaving the context, i.e. stopping the device server.

**Panel configuration**
- `maxi_synoptic_sim.yaml` uses full addresses `tango://localhost:45678/maxi/sim/1/<attr>#dbase=no`.
  Full `tango://` addresses already pass through unchanged (synoptic-config spec).
- Tests generate the same config with the test context's port filled in.

**Alternatives considered**
- *PyDM `loc://`*: doesn't go through the Tango plugin, has no INVALID quality, and has no `DevBoolean`
  as int.
- *TangoTest*: needs a Tango database, only has generic attribute names, and its quality can't be
  controlled.

### D14 Style sheet and plot redraw rate
Existing PyDM and Qt features are used instead of own code:
- `maxi_synoptic.qss` sets the font size and color of `PyDMLabel` and `ClockLabel`. The display loads it
  with `Display.setStyleSheet(<file>)`, so it applies to this display only and adds to PyDM's global
  style sheet (alarm borders, disconnected look). Sizes are in pixels and do not scale with the window.
- `defaults.max_redraw_rate` in the YAML is passed to `PyDMTimePlot.maxRedrawRate` of every plot.

### D15 Layout version 2
`MAXI_synoptic_v2.svg` is the SVG the panel loads. `MAXI_synoptic.svg` stays in the repository as the
first layout, but is not loaded anymore. Version 2 uses the same ids and:
- a dark theme with muted colors; only states and alarms are colored;
- a schematic band in the middle, with the panels above and below the hardware they belong to, so that
  no panel covers the hardware;
- value tiles with the caption above a 56 px high slot, for 30 px value text;
- valve and shutter drawn in the same way: a framed glyph with a word (`OPEN`, `CLOSED`, `?`) above it.
  The open shutter shows the beam passing, the closed one a blade that stops it;
- static hardware (shutter chamber, diff. pump) in a neutral color, because no rule colors it;
- a legend of the rule colors in the footer.

### D16 Beam path
`BEAM_axis` is the nominal path: a thin, dim, dashed line from the entry to the detector that is always
shown. `BEAM_entry` (entry to valve) is a static solid line. The rest of the beam is drawn by two more
state rules, with no change to the rule framework:
- `beam_after_valve` on channel `valve_open` shows `BEAM_VALVE_OPEN` or `BEAM_VALVE_CLOSED`. Its unknown
  asset is `BEAM_VALVE_OPEN` as well: a valve in an unknown state is drawn as letting the beam pass,
  because wrongly showing beam is the safer mistake.
- `beam_after_shutter` on channel `shutter_open` shows `BEAM_SHUTTER_OPEN`, `BEAM_SHUTTER_CLOSED` or
  `BEAM_SHUTTER_UNKNOWN`.

In the SVG, the three `BEAM_SHUTTER_*` groups lie inside the `BEAM_VALVE_OPEN` group. SVG hides the
children of a hidden group, so the beam behind the shutter needs both states without a rule that reads
two channels. The closed groups hold a stop mark. `BEAM_SHUTTER_UNKNOWN` holds stronger dashes that lie
exactly on the dashes of `BEAM_axis` (same dash pattern, shifted with `stroke-dashoffset`).

Several rules may now share a channel. Validation reports a missing channel once.
- *Alternative:* rules with several channels. Rejected: it changes the framework and the spec for
  something the SVG structure already gives.

## Risks / Trade-offs

- [`boundsOnElement` and `render(painter, id, bounds)` might handle the element's own transform
  differently from its ancestors' transforms] → Write tests with a small fixture SVG that has nested
  `translate()` transforms, and check overlay and hatching positions in pixels before building on it.
- [Re-rendering the whole SVG on every batched change costs more than a partial update] → At most
  10 Hz on a 1920x1080 SVG with a few hundred elements is fine. If profiling shows a problem, cache the
  rendered background as a pixmap.
- [Vented (> 700) and unknown share the same gray] → They differ only by the hatching, which is what was
  asked for. A different gray can be swapped in later through the constants.
- [`PYDM_TANGO_POLL_PERIOD` is global to the process] → It has no effect if another display loaded the
  plugin first. A warning covers this case.
- [The Tango plugin sends `DevBoolean` as an int] → State rules accept 0 and 1 as booleans. Any other
  int counts as unknown.
- [`DeviceTestContext` tests are slower and can fail on a port that is already taken] → Use them only
  in the simulator and integration tests, with an automatic port. The unit tests for rules and overlays
  feed values to the channel slots directly.
- [The simulator's attribute names drift away from the real devices] → It doesn't matter: the panel
  only knows addresses from the YAML, and the real names go into `maxi_synoptic.yaml`.
- [Device names in `maxi_synoptic.yaml` are placeholders] → Startup works with them, and the rules show
  unknown until real names are filled in.

## Migration Plan

Nothing to migrate, since this is a new panel. Roll back by not launching it.

## Open Questions

- The real Tango device and attribute names for `maxi_synoptic.yaml`. Filling them in changes only the
  YAML.
