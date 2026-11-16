"""The installed panel on the simulator device, through the real PyDM Tango plugin.

This is the only test that starts a device server. It loads the installed Designer file with the
installed style sheet and the macros that `maxi-synoptic` would pass for the simulator.
"""

import pytest
import tango
from pydm.display import load_file
from pydm.widgets import (
    PyDMDrawingCircle,
    PyDMDrawingRectangle,
    PyDMEmbeddedDisplay,
    PyDMLabel,
    PyDMTimePlot,
)
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
BEAM_Y = 552  # the dashed beam path of the drawing

GREEN, YELLOW, RED, BLUE, GRAY = "#4fae7b", "#d6a544", "#cf5b5b", "#4b8fc4", "#6b7480"
PURPLE, DARK, SILVER, AMBER = "#8e5ea2", "#262b31", "#aab4bf", "#f0c75e"
CLEAR = "clear"

# The valve's look: body fill, gate fills from top to bottom, shown words, and whether "?" is shown
VALVE_GATES = ("valve_gate_top", "valve_gate_upper", "valve_gate_lower", "valve_gate_bottom")
VALVE_LOOKS = {
    maxi_sim.VALVE_CLOSED: (RED, (DARK, DARK, DARK, DARK), ["CLOSED"], False),
    maxi_sim.VALVE_OPEN: (GREEN, (DARK, CLEAR, CLEAR, DARK), ["OPEN"], False),
    maxi_sim.VALVE_MOVING: (YELLOW, (DARK, DARK, CLEAR, DARK), ["MOVING"], False),
}
VALVE_UNKNOWN = (GRAY, (CLEAR, CLEAR, CLEAR, CLEAR), [], True)

# The shutter's look: frame pen, blade fills from top to bottom, shown words, and whether "?" is shown
SHUTTER_BLADES = ("shutter_blade_top", "shutter_blade_mid", "shutter_blade_bottom")
SHUTTER_LOOKS = {
    True: (AMBER, (SILVER, CLEAR, SILVER), ["OPEN"], False),
    False: (BLUE, (BLUE, BLUE, BLUE), ["CLOSED"], False),
}
SHUTTER_UNKNOWN = (GRAY, (CLEAR, CLEAR, CLEAR), [], True)


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
    for name in ("valve_state", "shutter_open", "maxi_vac_pressure", "diff_vac_pressure", "detector_temp"):
        initial = next(spec.initial for spec in maxi_sim.ATTRIBUTES if spec.name == name)
        device.write_attribute(name, initial)
    wait_for_initial_looks(qtbot, display, CONNECT_TIMEOUT_MS)


def wait_for_initial_looks(qtbot, display, timeout):
    wait_for_valve(qtbot, display, VALVE_LOOKS[maxi_sim.VALVE_CLOSED], timeout=timeout)
    wait_for_shutter(qtbot, display, SHUTTER_LOOKS[False], timeout=timeout)
    wait_for_fill(qtbot, display, "chamber", GREEN, timeout=timeout)
    wait_for_fill(qtbot, display, "diffpump", GREEN, timeout=timeout)
    wait_for_fill(qtbot, display, "detector", BLUE, timeout=timeout)


def shape(parent, name):
    return parent.findChild((PyDMDrawingCircle, PyDMDrawingRectangle), name)


def color_name(color):
    """The name of a colour, or "clear" if it is transparent."""
    if color.alpha() == 0:
        return CLEAR
    return color.name()


def fill_of(widget):
    """The fill colour of a shape, "hatched", or "clear"."""
    if widget.brush.style() == Qt.LinearGradientPattern:
        return "hatched"
    return color_name(QColor(widget.brush.color()))


def text_shown(display, label):
    """Whether a label is visible and its text is not transparent."""
    return label.isVisibleTo(display) and label.palette().color(label.foregroundRole()).alpha() > 0


def device_text(display, name):
    """The words shown by an embedded valve or shutter, and whether it shows "?"."""
    device = display.findChild(PyDMEmbeddedDisplay, name)
    labels = device.findChildren(PyDMLabel)
    words = [
        label.text() for label in labels if "_word_" in label.objectName() and text_shown(display, label)
    ]
    question_marks = [label for label in labels if label.text() == "?"]
    unknown = any(text_shown(display, label) for label in question_marks)
    return device, words, unknown


def valve_look(display):
    valve, words, unknown = device_text(display, "valve")
    gates = tuple(fill_of(shape(valve, name)) for name in VALVE_GATES)
    return fill_of(shape(valve, "valve_body")), gates, words, unknown


def shutter_look(display):
    shutter, words, unknown = device_text(display, "shutter")
    frame_pen = color_name(QColor(shape(shutter, "shutter_frame").penColor))
    blades = tuple(fill_of(shape(shutter, name)) for name in SHUTTER_BLADES)
    return frame_pen, blades, words, unknown


def wait_for_valve(qtbot, display, look, timeout=UPDATE_TIMEOUT_MS):
    qtbot.waitUntil(lambda: valve_look(display) == look, timeout=timeout)


def wait_for_shutter(qtbot, display, look, timeout=UPDATE_TIMEOUT_MS):
    qtbot.waitUntil(lambda: shutter_look(display) == look, timeout=timeout)


def label_of(display, signal):
    return next(label for label in display.findChildren(PyDMLabel) if f"/{signal}#" in label.channel)


def assert_borders_drawn(display):
    for name in ("chamber", "detector", "diffpump"):
        assert shape(display, name).penStyle == Qt.SolidLine, f"{name} has no border"


def wait_for_fill(qtbot, display, name, fill, timeout=UPDATE_TIMEOUT_MS):
    qtbot.waitUntil(lambda: fill_of(shape(display, name)) == fill, timeout=timeout)


def assert_screen_up_to_date(qtbot, display):
    """What is on screen equals a full repaint, in the row of the hardware.

    The valve and the shutter overlap the beam path and the pipes. A widget that paints only part of
    itself after a change would leave pieces of earlier states on screen.
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


def test_amplification_shows_power_of_ten(qtbot, display, simulator):
    # The device gives the exponent; a calc channel shows 10 to that power
    label = display.findChild(PyDMLabel, "DIODE_amplification_value")
    qtbot.waitUntil(lambda: label.text() == "1e+06", timeout=CONNECT_TIMEOUT_MS)
    simulator[0].device.diode_amplification = 9
    qtbot.waitUntil(lambda: label.text() == "1e+09", timeout=UPDATE_TIMEOUT_MS)
    simulator[0].device.diode_amplification = 6


@pytest.mark.parametrize(
    "mode, text",
    [(0, "HW AND SW"), (1, "HW OR SW"), (2, "SW ONLY"), (3, "HW ONLY"), (4, "UNKNOWN"), (-1, "UNKNOWN")],
)
def test_shutter_mode_shows_words(qtbot, display, simulator, mode, text):
    label = display.findChild(PyDMLabel, "SHUTTER_PANEL_mode_value")
    simulator[0].device.shutter_panel_mode = mode
    qtbot.waitUntil(lambda: label.text() == text, timeout=CONNECT_TIMEOUT_MS)
    simulator[0].device.shutter_panel_mode = 0


@pytest.mark.parametrize("mode, text", [(0, "OFF"), (1, "ON"), (2, "POWERSAVE"), (3, "UNKNOWN")])
def test_encoder_mode_shows_words(qtbot, display, simulator, mode, text):
    label = display.findChild(PyDMLabel, "DIODE_encoder_value")
    simulator[0].device.diode_encoder = mode
    qtbot.waitUntil(lambda: label.text() == text, timeout=CONNECT_TIMEOUT_MS)
    simulator[0].device.diode_encoder = 0


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


def painted_colors(qtbot, display, widget, points):
    """The colours on screen at points of a widget, given as fractions of its width and height."""
    qtbot.wait(PAINT_SETTLE_MS)
    image = display.grab().toImage()
    colors = set()
    for x_fraction, y_fraction in points:
        point = widget.mapTo(
            display, QPoint(int(widget.width() * x_fraction), int(widget.height() * y_fraction))
        )
        colors.add(QColor(image.pixel(point)).name())
    return colors


# Inside the differential pump stage, above the beam path
DIFFPUMP_POINTS = [(x / 20, 0.25) for x in range(4, 17)]


def test_diffpump_color_and_hatching(qtbot, display, simulator):
    device = simulator[0].device
    diffpump = shape(display, "diffpump")
    for pressure, color in ((1e-2, RED), (1013.0, GRAY), (5e-7, YELLOW)):
        device.diff_vac_pressure = pressure
        wait_for_fill(qtbot, display, "diffpump", color)
    assert painted_colors(qtbot, display, diffpump, DIFFPUMP_POINTS) == {YELLOW}

    device.SetInvalid("diff_vac_pressure")
    wait_for_fill(qtbot, display, "diffpump", "hatched")
    hatched = painted_colors(qtbot, display, diffpump, DIFFPUMP_POINTS)
    assert {GRAY, PURPLE} <= hatched and YELLOW not in hatched
    assert_borders_drawn(display)

    device.ClearInvalid("diff_vac_pressure")
    wait_for_fill(qtbot, display, "diffpump", YELLOW)


def test_valve_states(qtbot, display, simulator):
    device = simulator[0].device
    for state in (maxi_sim.VALVE_OPEN, maxi_sim.VALVE_MOVING, maxi_sim.VALVE_CLOSED, maxi_sim.VALVE_MOVING):
        device.valve_state = state
        wait_for_valve(qtbot, display, VALVE_LOOKS[state])
        assert_screen_up_to_date(qtbot, display)
    for value_without_state in (5, -1):
        device.valve_state = value_without_state
        wait_for_valve(qtbot, display, VALVE_UNKNOWN)
    device.valve_state = maxi_sim.VALVE_OPEN
    wait_for_valve(qtbot, display, VALVE_LOOKS[maxi_sim.VALVE_OPEN])
    assert_screen_up_to_date(qtbot, display)


def row_colors(image, device, y, x_range):
    points = (device.mapTo(device.window(), QPoint(x, y)) for x in range(*x_range))
    return {QColor(image.pixel(point)).name() for point in points}


# Inside the valve body and the shutter frame, clear of their outlines, in widget coordinates
INNER_X_RANGES = {"valve": (36, 160), "shutter": (36, 92)}


@pytest.mark.parametrize("name", list(INNER_X_RANGES))
def test_beam_path_drawn_over_valve_and_shutter(qtbot, display, name):
    """Along the beam path, the dashes add colours that the row just above it does not have."""
    device = display.findChild(PyDMEmbeddedDisplay, name)
    qtbot.wait(PAINT_SETTLE_MS)
    image = display.grab().toImage()
    beam_y = BEAM_Y - device.y()
    beam_row = row_colors(image, device, beam_y, INNER_X_RANGES[name])
    row_above = row_colors(image, device, beam_y - 8, INNER_X_RANGES[name])
    assert beam_row - row_above, f"no beam path drawn over the {name}"


def test_valve_invalid(qtbot, display, simulator):
    device = simulator[0].device
    device.valve_state = maxi_sim.VALVE_OPEN
    wait_for_valve(qtbot, display, VALVE_LOOKS[maxi_sim.VALVE_OPEN])
    device.SetInvalid("valve_state")
    wait_for_valve(qtbot, display, VALVE_UNKNOWN)
    assert_screen_up_to_date(qtbot, display)
    device.ClearInvalid("valve_state")
    wait_for_valve(qtbot, display, VALVE_LOOKS[maxi_sim.VALVE_OPEN])
    assert_screen_up_to_date(qtbot, display)


def test_shutter_states(qtbot, display, simulator):
    device = simulator[0].device
    for is_open in (True, False, True):
        device.shutter_open = is_open
        wait_for_shutter(qtbot, display, SHUTTER_LOOKS[is_open])
        assert_screen_up_to_date(qtbot, display)


def test_shutter_invalid(qtbot, display, simulator):
    device = simulator[0].device
    device.shutter_open = True
    wait_for_shutter(qtbot, display, SHUTTER_LOOKS[True])
    device.SetInvalid("shutter_open")
    wait_for_shutter(qtbot, display, SHUTTER_UNKNOWN)
    assert_screen_up_to_date(qtbot, display)
    device.ClearInvalid("shutter_open")
    wait_for_shutter(qtbot, display, SHUTTER_LOOKS[True])
    assert_screen_up_to_date(qtbot, display)


def test_neutral_words(qtbot, display, simulator):
    device = simulator[0].device
    device.valve_state = maxi_sim.VALVE_OPEN
    wait_for_valve(qtbot, display, VALVE_LOOKS[maxi_sim.VALVE_OPEN])
    word_colors = {
        label.palette().color(label.foregroundRole()).name()
        for label in display.findChildren(PyDMLabel)
        if "_word_" in label.objectName() and text_shown(display, label)
    }
    assert len(word_colors) == 1


def test_invalid_chamber(qtbot, display, simulator):
    device = simulator[0].device
    device.SetInvalid("maxi_vac_pressure")
    wait_for_fill(qtbot, display, "chamber", "hatched")
    device.ClearInvalid("maxi_vac_pressure")
    wait_for_fill(qtbot, display, "chamber", GREEN)


# Last in this file, because it stops the simulator
def test_simulator_stopped(qtbot, display, simulator):
    context = simulator[0]
    # the simulator looks like a real device: unit and format, types, and errors for wrong names
    pressure_config = context.device.get_attribute_config("maxi_vac_pressure")
    assert (pressure_config.unit, pressure_config.format) == ("mbar", "%.2e")
    assert context.device.get_attribute_config("shutter_open").data_type == tango.CmdArgType.DevBoolean
    assert context.device.get_attribute_config("valve_state").data_type == tango.CmdArgType.DevLong64
    with pytest.raises(tango.DevFailed):
        context.device.SetInvalid("no_such_attr")
    context.device.valve_state = maxi_sim.VALVE_OPEN
    wait_for_valve(qtbot, display, VALVE_LOOKS[maxi_sim.VALVE_OPEN])

    context.stop()
    wait_for_valve(qtbot, display, VALVE_UNKNOWN, timeout=DISCONNECT_TIMEOUT_MS)
    wait_for_shutter(qtbot, display, SHUTTER_UNKNOWN, timeout=DISCONNECT_TIMEOUT_MS)
    for name in ("chamber", "detector", "diffpump"):
        wait_for_fill(qtbot, display, name, "hatched", timeout=DISCONNECT_TIMEOUT_MS)
    assert_borders_drawn(display)
    assert_screen_up_to_date(qtbot, display)
    pressure_label = label_of(display, "maxi_vac_pressure")
    qtbot.waitUntil(lambda: pressure_label.alarmSeverity == DISCONNECTED, timeout=DISCONNECT_TIMEOUT_MS)
    assert pressure_label.text() == pressure_label.channel
