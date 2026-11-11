# MAXI synoptic panel

A PyDM panel that shows live Tango values on the MAXI synoptic drawing. It is made of PyDM's own
widgets only: a Qt Designer file, a style sheet and images exported from the drawing. The only Python
code is the command that starts it, and a simulator.

## Installation

The panel needs Python 3.10 or newer, PyQt5 with QtSvg, PyTango, and PyDM **with the Tango data
plugin**. The PyDM releases on PyPI and conda-forge have no Tango plugin; it is in the branch
`tango_plugin` of [dschick/pydm](https://github.com/dschick/pydm). Without it, the panel stops at
startup with an error that says so.

The panel also needs a PyDM in which `PyDMSymbol` draws its image into the whole widget on every
repaint. Older versions draw it squeezed into the repainted part, which leaves pieces of earlier
valve, shutter and beam states on screen. `tests/test_integration.py` fails with such a PyDM.

Install in this order, so that pip finds everything already there and changes nothing installed by
conda. PyQt5 must come from conda: pip does not install a Qt binding, and a pip PyQt5 next to the conda
one breaks the environment.

1. The conda packages (PyQt5, PyTango, and the dependencies of PyDM):

   ```sh
   mamba create -n maxi-synoptic -c conda-forge python=3.13 pytango=10.3 pyqt=5.15 pyqtgraph qtpy \
       six numpy entrypoints pyepics setuptools pytest pytest-qt pytest-timeout
   mamba activate maxi-synoptic
   ```

2. PyDM with the Tango plugin, without dependencies (they come from step 1). Either from a checkout of
   the fork next to this repository:

   ```sh
   pip install -e ../pydm --no-deps
   ```

   or directly from GitHub:

   ```sh
   pip install --no-deps "pydm @ git+https://github.com/dschick/pydm.git@tango_plugin"
   ```

3. The panel, from the checkout of this repository. Its own dependencies are only `pydm` and
   `pytango`:

   ```sh
   pip install .              # to run it
   pip install -e ".[test]"   # to work on it: editable, with the test dependencies
   ```

## Running the panel

```sh
maxi-synoptic                       # bundled configuration default.json
maxi-synoptic --config sim          # bundled configuration for the simulator
maxi-synoptic --config panel.json   # a configuration file, relative to the current directory
```

`--config` takes the name of a bundled configuration (`default` or `sim`) or a file path. A value with
a `/` or ending in `.json` is a path; anything else is a name. All other options go to PyDM unchanged,
for example `maxi-synoptic --config sim --hide-nav-bar`. `maxi-synoptic --help` shows PyDM's options.
PyDM's own `-m`/`--macro` option is not accepted; use `--config`.

The command checks the configuration (see [Configuration](#configuration)) and that the installed PyDM
has the Tango plugin, then starts PyDM with the installed Designer file `maxi_synoptic.ui`, the style
sheet `maxi_synoptic.qss` and the signals of the configuration as macros.

The panel has a fixed size of 1920x1080. It does not scale with the window: a larger window shows it in
the top-left corner, and on a smaller screen only its top-left part is visible.

How often the Tango plugin reads attributes that send no change events is set by the environment
variable `PYDM_TANGO_POLL_PERIOD`, in milliseconds:

```sh
PYDM_TANGO_POLL_PERIOD=500 maxi-synoptic --config sim
```

**BREAKING** (since the panel is a Designer file): the configuration is a JSON file, not YAML; see
[Migrating from the YAML configuration](#migrating-from-the-yaml-configuration). The local clock is
gone; its slot stays empty.

## Running the tests

```sh
pytest tests
```

The tests use the installed package (`pip install -e ".[test]"`), not the files of the checkout
directly. The integration test starts a Tango device server in a second process, on a free port, and
loads the installed panel offscreen against it. It needs no Tango database. `tests/test_ui.py` checks
the Designer file against the drawing, the exported images and the style sheet; `tests/test_assets.py`
checks that the exported images are up to date. `tests/test_packaging.py` builds a wheel and checks its
resource files and dependencies.

## Simulator

`maxi-synoptic-sim` starts a Tango device with a writable attribute for every signal of the panel. It runs without a Tango database:

```sh
maxi-synoptic-sim                 # port 45678, values change only when written
maxi-synoptic-sim --drift         # values change by themselves
maxi-synoptic-sim --port 45700
```

Start the panel on it in a second terminal:

```sh
maxi-synoptic --config sim
```

The `sim` configuration uses port 45678. Read, write and set the quality of an attribute from Python:

```python
import tango
sim = tango.DeviceProxy("tango://localhost:45678/maxi/sim/1#dbase=no")
sim.maxi_vac_pressure               # read
sim.maxi_vac_pressure = 1e-3        # write: the chamber turns yellow
sim.SetInvalid("shutter_open")      # INVALID quality: the shutter shows "?"
sim.ClearInvalid("shutter_open")
```

With `--drift`, the chamber pressure cycles between 1e-7 and 1000 mbar in 60 s (logarithmically), the
detector temperature between -40 and 30 °C in 40 s, the valve toggles every 10 s and the shutter every
7 s. Stop the simulator with Ctrl+C to see the disconnected look.

## Configuration

A configuration is a JSON file that maps each signal of the panel to the full channel address of its
Tango attribute:

```json
{
  "maxi_vac_pressure": "tango://maxi-ctrl:10000/maxi/vac/chamber_gauge/pressure",
  "valve_open": "tango://maxi-ctrl:10000/maxi/vac/valve/is_open",
  ...
}
```

The signal names are the simulator's attribute names: one per value slot, plus `valve_open` and
`shutter_open`. A signal can be used by several widgets: `maxi_vac_pressure` feeds the pressure label,
the pressure plot and the colour of the chamber. Every address is used as it is, so write it in full,
starting with `tango://<host>:<port>/`. Add `#dbase=no` for a device server without a Tango database.

The bundled files are `default.json` and `sim.json` in `src/maxi_synoptic/resources/`. **The Tango
device names in `default.json` are placeholders** until the real ones are known. To use other device
names, copy it, edit the copy and start the panel with `--config <copy>.json`.

Before PyDM starts, `maxi-synoptic` checks the file. If it is not valid JSON (the error names the line),
not a JSON object of strings, or lacks a signal that the panel uses, the panel does not start, and all
errors are reported together. A signal that the panel does not use is logged as a warning. Addresses
are not checked: a wrong address shows as a disconnected widget, with the address as its text.

Number formats, thresholds and plot settings are in the Designer file; see
[Changing the panel in Qt Designer](#changing-the-panel-in-qt-designer). Font size and colour of the
values are in the style sheet `maxi_synoptic.qss`.

### Migrating from the YAML configuration

| YAML | JSON |
|---|---|
| `values.<SLOT>.source` | the signal of the slot, e.g. `MAXI_VAC_pressure_value` → `maxi_vac_pressure` |
| `extra_channels.chamber_pressure` | `maxi_vac_pressure` |
| `extra_channels.detector_temperature` | `detector_temp` |
| `extra_channels.valve_open`, `shutter_open` | `valve_open`, `shutter_open` |
| `values.<SLOT>.format` | `displayFormat` and `precision` of the label in Qt Designer |
| `plots` | the plot's properties in Qt Designer |
| `defaults.tango_host` | none: write every address in full, `tango://<host>:<port>/...` |
| `defaults.tango_poll_period` | the environment variable `PYDM_TANGO_POLL_PERIOD`, in milliseconds |
| `defaults.max_redraw_rate` | `maxRedrawRate` of each plot in Qt Designer |
| `-m config=<file>` / `--config <file>.yaml` | `--config <file>.json` |

## Changing the panel in Qt Designer

Placement and widget settings are in `src/maxi_synoptic/resources/maxi_synoptic.ui`. Open it in Qt
Designer with PyDM's widgets:

```sh
PYQTDESIGNERPATH=$(python -c "import os, pydm; print(os.path.dirname(pydm.__file__))") \
    designer src/maxi_synoptic/resources/maxi_synoptic.ui
```

Designer prints `QDesignerPropertySheet::property(int) ... invalid index -1` for every label with a
format and for the plots. PyDM's own examples cause the same message; it does no harm.

Channels are written as macros, `${<signal>}`, filled from the configuration. A new signal in the `.ui`
must be added to both bundled configurations. In a `calc://` channel, use `${<signal>_calc}`, which the
command fills with the address with `#` encoded.

| To change | Widget | Property |
|---|---|---|
| number format of a value | the label, named after its slot, e.g. `MAXI_VAC_pressure_value` | `displayFormat` (`Exponential`, `Decimal` or `Default`), `precisionFromPV` (off to use `precision`), `precision`, `showUnits` |
| chamber or detector thresholds and colours | `chamber`, `detector` | `rules` (Edit Rules...): a Python expression such as `QColor('#4fae7b') if ch[0] <= 5e-6 else ...` |
| chamber or detector outline | `chamber`, `detector` | `penColor`, `penWidth`, `penStyle` (must stay `SolidLine`, or no outline is drawn) |
| time span of a plot | `MAXI_VAC_plot`, `SHUTTER_VAC_plot`, `DIFF_VAC_plot` | `timeSpan` (seconds) |
| how often a point is added | same | `updateMode` (`AtFixedRate`), `updateInterval` (seconds) |
| redraw rate | same | `maxRedrawRate` (per second) |
| y-axis | same | `yAxes`: `logMode`, `autoRange`, `minRange`/`maxRange` (powers of ten in log mode: `-9` is 1e-9) |
| curve and plot colours | same | `curves` (colour), `backgroundColor`, `axisColor` |
| state drawings | `valve`, `shutter`, `beam_valve`, `beam_shutter` | `imageFiles` (value → image). Change the same mapping in `maxi_synoptic.qss` (the rules for `alarmSeverity` 0 to 2) |

Unknown looks (hatching, UNKNOWN drawings, the INVALID and disconnected label styles) are set in
`maxi_synoptic.qss` by PyDM's `alarmSeverity` property: 3 is INVALID, 4 is disconnected.
`tests/test_ui.py` fails when a widget no longer matches the drawing, or the style sheet no longer
matches the `.ui`.

## Editing the SVG

`src/maxi_synoptic/resources/MAXI_synoptic_v2.svg` is the source of all graphics of the panel. The
panel does not read it: it shows images exported from it. After editing the drawing in Inkscape, export
the images and commit them together with the drawing:

```sh
python tools/export_assets.py
```

It writes into `src/maxi_synoptic/resources/assets/`: the background, the foreground, one image per
state drawing, an empty image per symbol and `symbols.json`, the crop of each symbol.
`tests/test_assets.py` fails while the committed images are out of date. With an editable install
(`pip install -e .`), the panel shows the new images on its next start; otherwise run `pip install .`
again. `MAXI.svg` and `MAXI_synoptic.svg` at the top of the repository are earlier layouts, kept for
reference; they are not installed.

The export finds elements by id (not by Inkscape label), so keep these:

| Id | Meaning |
|---|---|
| `layer_background`, `layer_panels` | layers drawn in the background image |
| `layer_hardware` | its elements before `MAXICHAMBER` go into the background image, those from `BEAM_axis` on into the foreground image |
| `layer_magnets`, `BEAM_entry` | drawn in the foreground image, above the chamber |
| `MAXICHAMBER`, `DETECTOR` | not exported: a PyDM circle and rectangle with the same geometry, outline colour and stroke width take their place. `DETECTOR` must keep square corners |
| `VALVE_OPEN`, `_CLOSED`, `_UNKNOWN`, `SHUTTER_OPEN`, `_CLOSED`, `_UNKNOWN` | state drawings of the valve and the shutter, one image each |
| `BEAM_VALVE_OPEN`, `_CLOSED` | the beam behind the valve, one image each |
| `BEAM_SHUTTER_OPEN`, `_CLOSED`, `_UNKNOWN` | the beam behind the shutter, one image each. The export removes them from the image of `BEAM_VALVE_OPEN` |

The state drawings of one symbol share one crop: the union of their bounds, plus room for the state
words above them. Their parent groups must have no transform, because the export copies them out.

**The widgets do not follow the drawing.** Labels, plots, the chamber and detector shapes and the
symbols are placed in the Designer file `maxi_synoptic.ui`. When a value slot (`<PANEL>_<signal>_value`),
a plot slot (`<PANEL>_plot`), `MAXICHAMBER` or `DETECTOR` moves or changes size, move or resize its
widget in Qt Designer as well. When the crop of a symbol changes, set its geometry from `symbols.json`.
`tests/test_ui.py` fails while a widget does not match the drawing.

## Layout of the code

The package `maxi_synoptic` is under `src/`:

| File | Content |
|---|---|
| `src/maxi_synoptic/cli.py` | the commands `maxi-synoptic` (configuration check, Tango plugin check, PyDM start) and `maxi-synoptic-sim` |
| `src/maxi_synoptic/sim.py` | simulator device |
| `src/maxi_synoptic/resources/maxi_synoptic.ui` | the panel: labels, plots, chamber and detector shapes with colour rules, state symbols, background and foreground images |
| `src/maxi_synoptic/resources/maxi_synoptic.qss` | style sheet: theme and unknown looks |
| `src/maxi_synoptic/resources/default.json`, `sim.json` | the bundled configurations |
| `src/maxi_synoptic/resources/MAXI_synoptic_v2.svg` | the drawing, source of all images |
| `src/maxi_synoptic/resources/assets/` | images exported from the drawing, and `symbols.json` |
| `tools/export_assets.py` | exports the images from the drawing; not installed |

## Demo check

Checked on 2026-11-11 with the Designer-file panel, the simulator (`maxi-synoptic-sim --drift`, as a
separate process) and the `sim` configuration. The panel was loaded offscreen with the installed `.ui`,
style sheet and macros, and its state was recorded every 0.5 s for 70 s (138 records), together with
screenshots:

- `MAXICHAMBER` was green, yellow and gray; `DETECTOR` was blue and gray.
- The valve showed `VALVE_OPEN` and `VALVE_CLOSED`, the shutter `SHUTTER_OPEN` and `SHUTTER_CLOSED`.
  The beam behind the valve followed the valve; the beam behind the shutter was absent (valve closed),
  `BEAM_SHUTTER_OPEN` or `BEAM_SHUTTER_CLOSED`.
- All 20 value labels showed values with units the whole time, and each plot had 73 points.
- 16.7 s after the simulator was stopped, `MAXICHAMBER` and `DETECTOR` were gray with purple hatching
  and kept their outlines, `VALVE_UNKNOWN` and `SHUTTER_UNKNOWN` were shown, the beam was solid through
  the valve and strongly dashed behind the shutter, and all labels had PyDM's disconnected look.
- 10.1 s after the simulator was started again, every colour, state and label was back.

INVALID quality is covered by `tests/test_integration.py`: the shutter shows `SHUTTER_UNKNOWN` and the
beam behind it keeps its last drawing.
