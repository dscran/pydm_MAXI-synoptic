"""The panel on the simulator device, through the real PyDM Tango plugin.

This is the only test that starts a device server. It stops the server at its end, and after that the
Tango client of this process gets no events from another test server anymore.
"""

import pytest
import tango
import yaml
from qtpy.QtCore import QPointF
from qtpy.QtGui import QColor
from tango.test_context import DeviceTestContext

from maxi_rules import GRAY, GREEN, YELLOW
from maxi_synoptic import MaxiSynoptic
from sim import maxi_sim
from sim.maxi_sim import MaxiSim

CONNECT_TIMEOUT_MS = 10000
UPDATE_TIMEOUT_MS = 5000
# Tango notices a stopped device server by missing heartbeats, which takes a while
DISCONNECT_TIMEOUT_MS = 40000
STATE_ASSETS = (
    "VALVE_OPEN",
    "VALVE_CLOSED",
    "VALVE_UNKNOWN",
    "SHUTTER_OPEN",
    "SHUTTER_CLOSED",
    "SHUTTER_UNKNOWN",
)


@pytest.fixture
def simulator():
    context = DeviceTestContext(MaxiSim, device_name=maxi_sim.DEVICE_NAME, process=True)
    context.start()
    yield context
    if context.thread.is_alive():
        context.stop()


@pytest.fixture
def display(qtbot, tmp_path, simulator):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump(maxi_sim.panel_config(f"{simulator.host}:{simulator.port}")))
    display = MaxiSynoptic(macros={"config": str(config_file)})
    qtbot.addWidget(display)
    display.resize(1920, 1080)
    display.show()
    qtbot.waitExposed(display)
    qtbot.waitUntil(
        lambda: not any(binding.is_unknown() for binding in display.rule_bindings), timeout=CONNECT_TIMEOUT_MS
    )
    return display


def label_of(display, attribute_name):
    return next(label for label in display.overlays.labels if f"/{attribute_name}#" in label.channel)


def visible_assets(display):
    return {asset for asset in STATE_ASSETS if display.view.is_visible(asset)}


def wait_for_fill(qtbot, display, element_id, color):
    qtbot.waitUntil(lambda: display.view.fill(element_id) == color, timeout=UPDATE_TIMEOUT_MS)


def test_panel_follows_the_simulator(qtbot, display, simulator):
    device = simulator.device
    view = display.view

    # the simulator looks like a real device: unit and format, booleans, and errors for wrong names
    pressure_config = device.get_attribute_config("maxi_vac_pressure")
    assert (pressure_config.unit, pressure_config.format) == ("mbar", "%.2e")
    assert device.get_attribute_config("valve_open").data_type == tango.CmdArgType.DevBoolean
    with pytest.raises(tango.DevFailed) as failure:
        device.SetInvalid("no_such_attr")
    assert "no_such_attr" in failure.value.args[0].desc

    # the initial values of the simulator: high vacuum, cold detector, valve and shutter closed
    assert view.fill("MAXICHAMBER") == GREEN
    assert view.hatched() == set()
    assert visible_assets(display) == {"VALVE_CLOSED", "SHUTTER_CLOSED"}

    # a value label shows a written value, with the format of the config and the unit from Tango
    pressure_label = label_of(display, "maxi_vac_pressure")
    device.maxi_vac_pressure = 1.2345e-5
    qtbot.waitUntil(lambda: pressure_label.text() == "1.23e-05 mbar", timeout=UPDATE_TIMEOUT_MS)
    # ... or with the Tango format, if the config has none
    energy_label = label_of(display, "beamline_energy")
    device.beamline_energy = 707.123
    qtbot.waitUntil(lambda: energy_label.text() == "707.12 eV", timeout=UPDATE_TIMEOUT_MS)
    status_label = label_of(display, "beamline_status")
    qtbot.waitUntil(lambda: status_label.text() == "ON", timeout=UPDATE_TIMEOUT_MS)

    # a plot grows a curve
    curve = display.overlays.plots[0].curveAtIndex(0)
    qtbot.waitUntil(lambda: curve.points_accumulated >= 2, timeout=UPDATE_TIMEOUT_MS)

    # the chamber color follows the pressure
    for pressure, color in ((1e-3, YELLOW), (1013.0, GRAY), (3e-7, GREEN)):
        device.maxi_vac_pressure = pressure
        wait_for_fill(qtbot, display, "MAXICHAMBER", color)
    assert view.hatched() == set()
    qtbot.wait(200)  # let the batched repaint happen
    chamber = view.element_rect("MAXICHAMBER")
    # above the centre, where neither the magnets nor the beam axis cover the fill
    fill_point = QPointF(chamber.center().x(), chamber.top() + 0.1 * chamber.height()).toPoint()
    assert QColor(view.grab().toImage().pixel(fill_point)).name() == GREEN

    # the valve attribute switches between the two assets
    device.valve_open = True
    qtbot.waitUntil(
        lambda: visible_assets(display) == {"VALVE_OPEN", "SHUTTER_CLOSED"}, timeout=UPDATE_TIMEOUT_MS
    )
    device.valve_open = False
    qtbot.waitUntil(
        lambda: visible_assets(display) == {"VALVE_CLOSED", "SHUTTER_CLOSED"}, timeout=UPDATE_TIMEOUT_MS
    )

    # INVALID quality hatches the chamber and shows the unknown shutter
    device.SetInvalid("maxi_vac_pressure")
    device.SetInvalid("shutter_open")
    qtbot.waitUntil(lambda: view.hatched() == {"MAXICHAMBER"}, timeout=UPDATE_TIMEOUT_MS)
    assert view.fill("MAXICHAMBER") == GRAY
    qtbot.waitUntil(
        lambda: visible_assets(display) == {"VALVE_CLOSED", "SHUTTER_UNKNOWN"}, timeout=UPDATE_TIMEOUT_MS
    )
    device.ClearInvalid("maxi_vac_pressure")
    device.ClearInvalid("shutter_open")
    wait_for_fill(qtbot, display, "MAXICHAMBER", GREEN)
    qtbot.waitUntil(
        lambda: visible_assets(display) == {"VALVE_CLOSED", "SHUTTER_CLOSED"}, timeout=UPDATE_TIMEOUT_MS
    )
