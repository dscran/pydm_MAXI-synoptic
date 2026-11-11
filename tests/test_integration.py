"""The installed panel on the simulator device, through the real PyDM Tango plugin.

This is the only test that starts a device server. It loads the installed Designer file with the
installed style sheet and the macros that `maxi-synoptic` would pass for the simulator.
"""

import json
from pathlib import Path

import pytest
import tango
from pydm.display import load_file
from pydm.widgets import PyDMDrawingCircle, PyDMDrawingRectangle, PyDMLabel, PyDMSymbol, PyDMTimePlot
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtGui import QColor
from tango.test_context import DeviceTestContext

from maxi_synoptic import sim as maxi_sim
from maxi_synoptic.cli import STYLE_SHEET, UI_FILE, panel_macros
from maxi_synoptic.sim import MaxiSim

CONNECT_TIMEOUT_MS = 10000
UPDATE_TIMEOUT_MS = 5000
# Tango notices a stopped device server by missing heartbeats, which takes a while
DISCONNECT_TIMEOUT_MS = 40000
DISCONNECTED = 4
PAINT_SETTLE_MS = 200
HARDWARE_ROW = QRect(0, 380, 1920, 340)

GREEN, YELLOW, BLUE, GRAY = "#4fae7b", "#d6a544", "#4b8fc4", "#6b7480"
# Valve and shutter closed: the initial state of the simulator
BOTH_CLOSED = {
    "valve": "VALVE_CLOSED",
    "beam_valve": "BEAM_VALVE_CLOSED",
    "shutter": "SHUTTER_CLOSED",
    "beam_shutter": "beam_shutter_none",
}


def start_simulator():
    context = DeviceTestContext(MaxiSim, device_name=maxi_sim.DEVICE_NAME, process=True)
    context.start()
    return context


@pytest.fixture(scope="module")
def simulator():
    context = start_simulator()
    yield [context]
    if context.thread.is_alive():
        context.stop()


@pytest.fixture(scope="module")
def display(qapp, simulator):
    # One display for all tests: after a display is closed, PyDM's rules engine stops evaluating the
    # rules of the next one in the same process.
    context = simulator[0]
    macros = panel_macros(maxi_sim.panel_signals(f"{context.host}:{context.port}"))
    qapp.setStyleSheet(STYLE_SHEET.read_text())
    display = load_file(str(UI_FILE), macros=macros, target=None)
    display.show()
    yield display
    display.close()
    qapp.setStyleSheet("")


@pytest.fixture(autouse=True)
def initial_values(qtbot, display, simulator):
    """Start every test from the initial values of the simulator: both closed, green, blue."""
    device = simulator[0].device
    for name in ("valve_open", "shutter_open", "maxi_vac_pressure", "detector_temp"):
        initial = next(spec.initial for spec in maxi_sim.ATTRIBUTES if spec.name == name)
        device.write_attribute(name, initial)
    qtbot.waitUntil(lambda: shown_drawings(display) == BOTH_CLOSED, timeout=CONNECT_TIMEOUT_MS)
    wait_for_fill(qtbot, display, "chamber", GREEN, timeout=CONNECT_TIMEOUT_MS)


def shown_drawings(display):
    """The drawing that each symbol shows, by symbol name, e.g. {"valve": "VALVE_OPEN", ...}."""
    return {symbol.objectName(): shown_drawing(symbol) for symbol in display.findChildren(PyDMSymbol)}


def shown_drawing(symbol):
    # PyDMSymbol has no public getter for its current value
    image_files = json.loads(symbol.imageFiles)
    return Path(image_files[str(int(symbol._current_key))]).stem


def shape(display, name):
    return display.findChild((PyDMDrawingCircle, PyDMDrawingRectangle), name)


def fill_of(widget):
    """The fill colour of a shape, or "hatched"."""
    if widget.brush.style() == Qt.LinearGradientPattern:
        return "hatched"
    return QColor(widget.brush.color()).name()


def label_of(display, signal):
    return next(label for label in display.findChildren(PyDMLabel) if f"/{signal}#" in label.channel)


def assert_borders_drawn(display):
    for name in ("chamber", "detector"):
        assert shape(display, name).penStyle == Qt.SolidLine, f"{name} has no border"


def wait_for_fill(qtbot, display, name, fill, timeout=UPDATE_TIMEOUT_MS):
    qtbot.waitUntil(lambda: fill_of(shape(display, name)) == fill, timeout=timeout)


def wait_for_drawings(qtbot, display, expected, timeout=UPDATE_TIMEOUT_MS):
    qtbot.waitUntil(lambda: shown_drawings(display).items() >= expected.items(), timeout=timeout)


def assert_screen_up_to_date(qtbot, display):
    """What is on screen equals a full repaint, in the row of the hardware.

    Symbols overlap each other and the chamber. A symbol that paints only part of itself correctly
    after a neighbour changed leaves pieces of earlier states on screen (fixed in PyDMSymbol).
    """
    qtbot.wait(PAINT_SETTLE_MS)
    on_screen = display.screen().grabWindow(display.winId()).toImage().copy(HARDWARE_ROW)
    repainted = display.grab().toImage().copy(HARDWARE_ROW)
    differing = [
        (x, y)
        for x in range(HARDWARE_ROW.width())
        for y in range(HARDWARE_ROW.height())
        if on_screen.pixel(x, y) != repainted.pixel(x, y)
    ]
    assert differing == [], f"{len(differing)} pixels differ on screen, first at {differing[0]}"


def test_values_have_units_and_formats(qtbot, display, simulator):
    device = simulator[0].device
    pressure_label = label_of(display, "maxi_vac_pressure")
    device.maxi_vac_pressure = 1.2345e-5
    qtbot.waitUntil(lambda: pressure_label.text() == "1.23e-05 mbar", timeout=UPDATE_TIMEOUT_MS)
    # the Tango format, where the .ui sets none
    energy_label = label_of(display, "beamline_energy")
    device.beamline_energy = 707.123
    qtbot.waitUntil(lambda: energy_label.text() == "707.12 eV", timeout=UPDATE_TIMEOUT_MS)
    status_label = label_of(display, "beamline_status")
    qtbot.waitUntil(lambda: status_label.text() == "ON", timeout=UPDATE_TIMEOUT_MS)
    # a plot adds points at a fixed rate, also while the value does not change
    curve = display.findChild(PyDMTimePlot, "MAXI_VAC_plot").curveAtIndex(0)
    qtbot.waitUntil(lambda: curve.points_accumulated >= 2, timeout=UPDATE_TIMEOUT_MS)


def test_chamber_and_detector_colors(qtbot, display, simulator):
    device = simulator[0].device
    wait_for_fill(qtbot, display, "detector", BLUE)
    for pressure, color in ((1e-3, YELLOW), (1013.0, GRAY), (3e-7, GREEN)):
        device.maxi_vac_pressure = pressure
        wait_for_fill(qtbot, display, "chamber", color)
        assert_screen_up_to_date(qtbot, display)
    device.detector_temp = 22.0
    wait_for_fill(qtbot, display, "detector", GRAY)
    device.detector_temp = -40.0
    wait_for_fill(qtbot, display, "detector", BLUE)
    assert_borders_drawn(display)

    # the colour is painted: above the chamber's centre, where neither magnets nor beam cover it
    chamber = shape(display, "chamber")
    qtbot.wait(200)
    point = chamber.mapTo(display, QPoint(chamber.width() // 2, chamber.height() // 10))
    assert QColor(display.grab().toImage().pixel(point)).name() == GREEN


def test_valve_shutter_and_beam(qtbot, display, simulator):
    device = simulator[0].device
    device.valve_open = True
    wait_for_drawings(
        qtbot,
        display,
        {
            "valve": "VALVE_OPEN",
            "beam_valve": "BEAM_VALVE_OPEN",
            "shutter": "SHUTTER_CLOSED",
            "beam_shutter": "BEAM_SHUTTER_CLOSED",
        },
    )
    assert_screen_up_to_date(qtbot, display)
    device.shutter_open = True
    wait_for_drawings(qtbot, display, {"shutter": "SHUTTER_OPEN", "beam_shutter": "BEAM_SHUTTER_OPEN"})
    assert_screen_up_to_date(qtbot, display)
    device.valve_open = False
    wait_for_drawings(
        qtbot,
        display,
        {
            "valve": "VALVE_CLOSED",
            "beam_valve": "BEAM_VALVE_CLOSED",
            "shutter": "SHUTTER_OPEN",
            "beam_shutter": "beam_shutter_none",
        },
    )
    assert_screen_up_to_date(qtbot, display)


def test_invalid_quality(qtbot, display, simulator):
    device = simulator[0].device
    device.valve_open = True
    device.shutter_open = True
    wait_for_drawings(qtbot, display, {"shutter": "SHUTTER_OPEN", "beam_shutter": "BEAM_SHUTTER_OPEN"})

    device.SetInvalid("shutter_open")
    device.SetInvalid("maxi_vac_pressure")
    wait_for_drawings(qtbot, display, {"shutter": "SHUTTER_UNKNOWN"})
    wait_for_fill(qtbot, display, "chamber", "hatched")
    # the calc channel of the beam behind the shutter does not pass the quality on
    assert shown_drawings(display)["beam_shutter"] == "BEAM_SHUTTER_OPEN"

    device.ClearInvalid("shutter_open")
    device.ClearInvalid("maxi_vac_pressure")
    wait_for_drawings(qtbot, display, {"shutter": "SHUTTER_OPEN"})
    wait_for_fill(qtbot, display, "chamber", GREEN)


# Last in this file, because it stops the simulator
def test_simulator_stopped(qtbot, display, simulator):
    context = simulator[0]
    # the simulator looks like a real device: unit and format, booleans, and errors for wrong names
    pressure_config = context.device.get_attribute_config("maxi_vac_pressure")
    assert (pressure_config.unit, pressure_config.format) == ("mbar", "%.2e")
    assert context.device.get_attribute_config("valve_open").data_type == tango.CmdArgType.DevBoolean
    with pytest.raises(tango.DevFailed):
        context.device.SetInvalid("no_such_attr")

    context.stop()
    unknown = {
        "valve": "VALVE_UNKNOWN",
        "beam_valve": "BEAM_VALVE_OPEN",
        "shutter": "SHUTTER_UNKNOWN",
        "beam_shutter": "BEAM_SHUTTER_UNKNOWN",
    }
    wait_for_drawings(qtbot, display, unknown, timeout=DISCONNECT_TIMEOUT_MS)
    wait_for_fill(qtbot, display, "chamber", "hatched", timeout=DISCONNECT_TIMEOUT_MS)
    wait_for_fill(qtbot, display, "detector", "hatched", timeout=DISCONNECT_TIMEOUT_MS)
    assert_borders_drawn(display)
    pressure_label = label_of(display, "maxi_vac_pressure")
    qtbot.waitUntil(lambda: pressure_label.alarmSeverity == DISCONNECTED, timeout=DISCONNECT_TIMEOUT_MS)
    assert pressure_label.text() == pressure_label.channel
