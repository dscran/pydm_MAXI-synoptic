# MAXI synoptic panel

A PyDM panel that shows live Tango values on the MAXI synoptic drawing. It is made of PyDM's own
widgets only: Qt Designer files, a style sheet and images exported from the drawing. The only Python
code is the command that starts it, and a simulator.

## Installation

The panel needs Python 3.10 or newer, PyQt5 with QtSvg, PyTango, and PyDM **with the Tango data
plugin**. The PyDM releases on PyPI and conda-forge have no Tango plugin; it is in the branch
`tango_plugin` of [dschick/pydm](https://github.com/dschick/pydm). Without it, the panel stops at
startup with an error that says so. The valve and the shutter use `displayLabelText` of `PyDMLabel`,
which is in PyDM 1.29 and newer; the `tango_plugin` branch has it.

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
the Designer files against the drawing, the looks of the valve and the shutter, and the style sheet; `tests/test_assets.py`
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

The valve attribute `valve_state` is an integer: 0 is CLOSED, 1 is OPEN, 2 is MOVING; the panel shows
any other value like an unknown one, with `?`. The shutter
attribute `shutter_open` is a boolean.

With `--drift`, the chamber pressure cycles between 1e-7 and 1000 mbar in 60 s and the differential
pump stage pressure between 1e-8 and 1000 mbar in 50 s (both logarithmically), the detector
temperature between -40 and 30 °C in 40 s, the valve is CLOSED for 10 s, MOVING for 3 s, OPEN for
10 s and MOVING for 3 s, and the shutter toggles every 7 s. Stop the simulator with Ctrl+C to see the
disconnected look.

## Configuration

A configuration is a JSON file that maps each signal of the panel to the full channel address of its
Tango attribute:

```json
{
  "maxi_vac_pressure": "tango://maxi-ctrl:10000/maxi/vac/chamber_gauge/pressure",
  "valve_state": "tango://maxi-ctrl:10000/maxi/vac/valve/state",
  ...
}
```

The signal names are the simulator's attribute names: one per value slot, plus `valve_state` (an
integer: 0 CLOSED, 1 OPEN, 2 MOVING; any other value shows `?`) and `shutter_open` (a boolean). A signal can be used by several widgets: `maxi_vac_pressure` feeds the pressure label,
the pressure plot and the colour of the chamber. Every address is used as it is, so write it in full,
starting with `tango://<host>:<port>/`. Add `#dbase=no` for a device server without a Tango database.

The bundled files are `default.json` and `sim.json` in `src/maxi_synoptic/resources/`. **The Tango
device names in `default.json` are placeholders** until the real ones are known. To use other device
names, copy it, edit the copy and start the panel with `--config <copy>.json`.

Before PyDM starts, `maxi-synoptic` checks the file. If it is not valid JSON (the error names the line),
not a JSON object of strings, or lacks a signal that the panel uses, the panel does not start, and all
errors are reported together. A signal that the panel does not use is logged as a warning. Addresses
are not checked: a wrong address shows as a disconnected widget, with the address as its text.

**BREAKING** (since the valve has a MOVING state): the signal `valve_open` (boolean) is replaced by
`valve_state` (integer: 0 CLOSED, 1 OPEN, 2 MOVING). Rename it in your configuration and point it to
an integer attribute. Until then, the panel does not start and reports that `valve_state` is missing.

Number formats, thresholds and plot settings are in the Designer file; see
[Changing the panel in Qt Designer](#changing-the-panel-in-qt-designer). Font size and colour of the
values are in the style sheet `maxi_synoptic.qss`.

### Migrating from the YAML configuration

| YAML | JSON |
|---|---|
| `values.<SLOT>.source` | the signal of the slot, e.g. `MAXI_VAC_pressure_value` → `maxi_vac_pressure` |
| `extra_channels.chamber_pressure` | `maxi_vac_pressure` |
| `extra_channels.detector_temperature` | `detector_temp` |
| `extra_channels.valve_open`, `shutter_open` | `valve_state` (an integer attribute, see above), `shutter_open` |
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
command fills with the address with `#` encoded. `DIODE_amplification_value` does so: the device gives the
exponent of the gain, and `calc://diode_amplification?x=${diode_amplification_calc}&expr=10**x` shows
10 to that power. `SHUTTER_PANEL_mode_value` turns the integer shutter mode into words the same way, with
`expr={0: 'HW AND SW', 1: 'HW OR SW', 2: 'SW ONLY', 3: 'HW ONLY'}.get(x, 'UNKNOWN')`, and
`DIODE_encoder_value` the encoder sensor mode with `expr={0: 'OFF', 1: 'ON', 2: 'POWERSAVE'}.get(x, 'UNKNOWN')`.

| To change | Widget | Property |
|---|---|---|
| number format of a value | the label, named after its slot, e.g. `MAXI_VAC_pressure_value` | `displayFormat` (`Exponential`, `Decimal` or `Default`), `precisionFromPV` (off to use `precision`), `precision`, `showUnits` |
| chamber, differential pump stage or detector thresholds and colours | `chamber`, `diffpump`, `detector` | `rules` (Edit Rules...): a Python expression such as `QColor('#4fae7b') if ch[0] <= 5e-6 else ...` |
| chamber, differential pump stage or detector outline | `chamber`, `diffpump`, `detector` | `penColor`, `penWidth`, `penStyle` (must stay `SolidLine`, or no outline is drawn) |
| time span of a plot | `MAXI_VAC_plot`, `SHUTTER_VAC_plot`, `DIFF_VAC_plot` | `timeSpan` (seconds) |
| how often a point is added | same | `updateMode` (`AtFixedRate`), `updateInterval` (seconds) |
| redraw rate | same | `maxRedrawRate` (per second) |
| y-axis | same | `yAxes`: `logMode`, `autoRange`, `minRange`/`maxRange` (powers of ten in log mode: `-9` is 1e-9) |
| curve and plot colours | same | `curves` (colour), `backgroundColor`, `axisColor` |
| position of the valve or the shutter | `valve`, `shutter` (a `PyDMEmbeddedDisplay` each) | `geometry`: move the one widget, and its body, gate or blades, word and `?` move with it |
| look of the valve or the shutter | the parts in `valve.ui`, `shutter.ui` | open the file itself in Qt Designer: `rules` of each part (body colour, gate or blades, which word is shown), geometry of the parts |
| channel of the valve or the shutter | `valve`, `shutter` | `macros`: `{"ch": "${valve_state}"}`. Every part in `valve.ui` and `shutter.ui` uses `${ch}`, so a second valve is a second embedded display with another signal |

Unknown looks (hatching, the gray valve and shutter with `?`, the INVALID and disconnected label
styles) are set in `maxi_synoptic.qss` by PyDM's `alarmSeverity` property: 3 is INVALID, 4 is
disconnected. The style sheet sets brushes and pens of the valve and the shutter only at 3 and 4; at 0
to 2 their rules own them. The state words have one colour, set in the style sheet.
`tests/test_ui.py` fails when a widget no longer matches the drawing, or the style sheet no longer
matches the `.ui`.

## Editing the SVG

`src/maxi_synoptic/resources/MAXI_synoptic_v2.svg` is the source of all graphics of the panel. The
panel does not read it: it shows images exported from it. After editing the drawing in Inkscape, export
the images and commit them together with the drawing:

```sh
python tools/export_assets.py
```

It writes the background and the foreground into `src/maxi_synoptic/resources/assets/`. The drawing
has no valve or shutter states and no reactive beam: the valve and the shutter are drawn by `valve.ui`
and `shutter.ui`, and the beam is only the dashed path and its arrow.
`tests/test_assets.py` fails while the committed images are out of date. With an editable install
(`pip install -e .`), the panel shows the new images on its next start; otherwise run `pip install .`
again. `MAXI.svg` and `MAXI_synoptic.svg` at the top of the repository are earlier layouts, kept for
reference; they are not installed.

The export finds elements by id (not by Inkscape label), so keep these:

| Id | Meaning |
|---|---|
| `layer_background`, `layer_panels` | layers drawn in the background image |
| `layer_hardware` | its elements before `DIFFPUMP` go into the background image, those from `BEAM_axis` on into the foreground image |
| `layer_magnets` | drawn in the foreground image, above the chamber |
| `DIFFPUMP`, `MAXICHAMBER`, `DETECTOR` | not exported: PyDM shapes `diffpump`, `chamber` and `detector` with the same geometry, outline colour and stroke width take their place. `DIFFPUMP` and `DETECTOR` must keep square corners, and `DIFFPUMP` must stay the first of the three |

The foreground image is drawn over the PyDM shapes and also over the valve and the shutter, so that the
dashed beam path `BEAM_axis` crosses them. Keep anything else in the foreground out of their area.

**The widgets do not follow the drawing.** Labels, plots, the shapes of the differential pump stage, the
chamber and the detector, and the valve and the shutter are placed in the Designer file
`maxi_synoptic.ui`. When a value slot (`<PANEL>_<signal>_value`), a plot slot (`<PANEL>_plot`),
`DIFFPUMP`, `MAXICHAMBER` or `DETECTOR` moves or changes size, move or resize its widget in Qt Designer
as well. `tests/test_ui.py` fails while a widget does not match the drawing.

## Layout of the code

The package `maxi_synoptic` is under `src/`:

| File | Content |
|---|---|
| `src/maxi_synoptic/cli.py` | the commands `maxi-synoptic` (configuration check, Tango plugin check, PyDM start) and `maxi-synoptic-sim` |
| `src/maxi_synoptic/sim.py` | simulator device |
| `src/maxi_synoptic/resources/maxi_synoptic.ui` | the panel: labels, plots, differential pump stage, chamber and detector shapes with colour rules, the embedded valve and shutter, background and foreground images |
| `src/maxi_synoptic/resources/valve.ui`, `shutter.ui` | the valve and the shutter: PyDM shapes and labels with rules on the channel `${ch}` |
| `src/maxi_synoptic/resources/maxi_synoptic.qss` | style sheet: theme and unknown looks |
| `src/maxi_synoptic/resources/default.json`, `sim.json` | the bundled configurations |
| `src/maxi_synoptic/resources/MAXI_synoptic_v2.svg` | the drawing, source of all images |
| `src/maxi_synoptic/resources/assets/` | the background and foreground images exported from the drawing |
| `tools/export_assets.py` | exports the images from the drawing; not installed |

## Demo check

Checked on 2026-11-14 with the panel built from the embedded valve and shutter, the simulator
(`maxi-synoptic-sim --drift`, as a separate process) and the `sim` configuration. The panel was loaded
offscreen with the installed `.ui` files, style sheet and macros, and its state was recorded every
0.5 s for about 60 s (120 records), together with screenshots:

- The valve went CLOSED (red), MOVING (amber), OPEN (green), MOVING, CLOSED, ... in this order, with one
  word at a time. The shutter showed OPEN and CLOSED.
- `DIFFPUMP` was green, yellow, red and gray; `MAXICHAMBER` green, yellow and gray; `DETECTOR` blue and
  gray. The dashed beam path and its arrow were drawn in every state.
- All 20 value labels showed values the whole time, and each plot had 66 or 67 points.
- 12.8 s after the simulator was stopped, the valve showed a gray body with `?` and the shutter a gray
  frame with `?`, neither with gate, blades or word; `MAXICHAMBER`, `DETECTOR` and `DIFFPUMP` were gray
  with purple hatching and kept their outlines; all labels had PyDM's disconnected look.
- 10.2 s after the simulator was started again (without drift), the valve and the shutter showed CLOSED,
  every colour was back, and all labels showed values.

INVALID quality is covered by `tests/test_integration.py`: the valve, the shutter and the differential
pump stage show their unknown looks, and their states come back with `ClearInvalid`.
