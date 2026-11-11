# MAXI synoptic panel

A PyDM panel that renders `MAXI_synoptic_v2.svg` and shows live Tango values on it.
(`MAXI_synoptic.svg` is the first layout. It is kept for reference and is not loaded.)

## Environment

The panel needs PyDM with the Tango data plugin (the checkout in `../pydm`), PyTango, PyQt5 with QtSvg,
pyqtgraph and PyYAML. The tests also need pytest, pytest-qt and pytest-timeout.

The commands below use the conda environment `maxi-synoptic`:

```sh
mamba create -n maxi-synoptic -c conda-forge python=3.13 pytango=10.3 pyqt=5.15 pyqtgraph pyyaml \
    qtpy six numpy entrypoints pyepics pytest pytest-qt pytest-timeout
mamba activate maxi-synoptic
export PYTHONPATH=../pydm
```

The pixi environment of `../pydm` works the same way, if it is installed on your machine: run the
commands with `pixi run --manifest-path ../pydm`, and keep `PYTHONPATH=../pydm`.

## Running the panel

```sh
python -m pydm_launcher.main maxi_synoptic.py
```

The panel reads `maxi_synoptic.yaml` next to `maxi_synoptic.py`. The macro `config` names another
file, relative to the same directory:

```sh
python -m pydm_launcher.main -m config=maxi_synoptic_sim.yaml maxi_synoptic.py
```

## Running the tests

```sh
pytest tests
```

The integration test and the simulator tests start a Tango device server in a second process, on a free
port. They need no Tango database.

## Simulator

`sim/maxi_sim.py` is a Tango device with a writable attribute for every value slot and rule channel of
the panel. It runs without a Tango database:

```sh
python sim/maxi_sim.py            # port 45678, values change only when written
python sim/maxi_sim.py --drift    # values change by themselves
python sim/maxi_sim.py --port 45700
```

Start the panel on it in a second terminal:

```sh
python -m pydm_launcher.main -m config=maxi_synoptic_sim.yaml maxi_synoptic.py
```

`maxi_synoptic_sim.yaml` uses port 45678. Read, write and set the quality of an attribute from Python:

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

`maxi_synoptic.yaml` explains every key in its comments. **Its Tango device names are placeholders**
until the real ones are known. A wrong configuration stops the panel at startup with a list of all
errors; inconsistencies that still allow a start are logged as warnings.

Font size and color of the values and of the clock are in the Qt style sheet `maxi_synoptic.qss`. The
panel is made for a window of 1920x1080: the drawing scales with the window, but the fonts do not.

Colors and states are rules in `maxi_rules.py`. Each rule reads one channel from the `extra_channels`
section of the YAML.

## Editing the SVG

Edit `MAXI_synoptic_v2.svg` in Inkscape and save it as usual. The panel only looks at element ids (not
Inkscape labels), so keep these:

| Id | Meaning |
|---|---|
| `<PANEL>_<signal>_value` | value slot, covered by a value label |
| `<PANEL>_plot` | plot slot, covered by a time plot |
| `DATETIME_value` | shows the local date and time |
| `<X>_OPEN`, `<X>_CLOSED`, `<X>_UNKNOWN` | three drawings of a valve or shutter; the panel shows one of them |
| `MAXICHAMBER`, `DETECTOR` | the panel sets their fill color and hatches them while the value is unknown |
| `BACKGROUND` | its fill color is used around the drawing |

Elements may be moved, resized, grouped and transformed freely. The comment at the top of the SVG file
is not read by the panel; its "no transforms" rule no longer applies.

## Layout of the code

| File | Content |
|---|---|
| `maxi_synoptic.py` | the PyDM display |
| `maxi_synoptic.qss` | font size and color of the values and the clock |
| `maxi_rules.py` | MAXI color and state rules |
| `synoptic/config.py` | YAML loading, schema, Tango addresses, printf formats |
| `synoptic/validation.py` | checks of the configuration and the rules against the SVG |
| `synoptic/poll_period.py` | poll period of the Tango plugin |
| `synoptic/svg_view.py` | SVG document and widget: drawing, coordinates, hatching |
| `synoptic/overlays.py` | value labels, time plots and the clock |
| `synoptic/rules.py` | rule framework |
| `sim/maxi_sim.py` | simulator device |

## Demo check

Checked on 2026-11-11 with `python sim/maxi_sim.py --drift` and `config=maxi_synoptic_sim.yaml`. The
panel ran with `QT_QPA_PLATFORM=offscreen`, and its state was recorded every 0.5 s for 70 s, together
with screenshots:

- `MAXICHAMBER` was green, yellow and gray; `DETECTOR` was blue and gray.
- `VALVE_OPEN`/`VALVE_CLOSED` and `SHUTTER_OPEN`/`SHUTTER_CLOSED` alternated.
- All value labels showed values with units, and the plots drew curves.
- 8.5 s after the simulator was stopped, `MAXICHAMBER` and `DETECTOR` were gray with purple hatching,
  `VALVE_UNKNOWN` and `SHUTTER_UNKNOWN` were shown, and the labels had PyDM's disconnected look.

Known cosmetic issue: a logarithmic plot of a value that never changes shows overlapping y-axis tick
labels, because the axis has no range to scale to.
