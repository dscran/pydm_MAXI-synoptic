"""The parts of the simulator that need no device server. The device itself is used by test_integration."""

import math

import pytest

from sim import maxi_sim
from sim.maxi_sim import ATTRIBUTES, ATTRIBUTE_NAMES, PLOTTED, RULE_CHANNELS


def test_rule_channels_and_plots_use_existing_attributes():
    assert set(RULE_CHANNELS.values()) <= set(ATTRIBUTE_NAMES)
    assert set(PLOTTED.values()) <= set(ATTRIBUTE_NAMES)


def test_attribute_types():
    types = {spec.name: spec.dtype for spec in ATTRIBUTES}
    assert types["maxi_vac_pressure"] is float
    assert types["beamline_status"] is str
    assert types["valve_open"] is bool and types["shutter_open"] is bool


def test_only_drifting_attributes_change():
    assert set(maxi_sim.drift_values(3)) == {
        "maxi_vac_pressure",
        "detector_temp",
        "valve_open",
        "shutter_open",
    }


def test_triangle():
    assert maxi_sim.triangle(0, 60) == 0
    assert maxi_sim.triangle(15, 60) == pytest.approx(0.5)
    assert maxi_sim.triangle(30, 60) == pytest.approx(1)
    assert maxi_sim.triangle(45, 60) == pytest.approx(0.5)
    assert maxi_sim.triangle(60, 60) == 0


def test_pressure_cycle_shows_every_chamber_color():
    ticks = int(maxi_sim.PRESSURE_PERIOD_SECONDS / maxi_sim.DRIFT_TICK_SECONDS)
    pressures = [maxi_sim.drift_pressure(tick * maxi_sim.DRIFT_TICK_SECONDS) for tick in range(ticks + 1)]
    assert min(pressures) == pytest.approx(1e-7)
    assert max(pressures) == pytest.approx(1000)
    assert any(pressure <= 5e-6 for pressure in pressures)
    assert any(5e-6 < pressure <= 700 for pressure in pressures)
    assert any(pressure > 700 for pressure in pressures)
    # logarithmic: the middle of the rising edge is the geometric mean
    assert maxi_sim.drift_pressure(15) == pytest.approx(math.sqrt(1e-7 * 1000))


def test_temperature_cycle_shows_both_detector_colors():
    temperatures = [maxi_sim.drift_temperature(second) for second in range(41)]
    assert min(temperatures) == pytest.approx(-40)
    assert max(temperatures) == pytest.approx(30)


def test_valve_and_shutter_toggle_at_different_intervals():
    assert [maxi_sim.drift_toggle(second, 10) for second in (0, 9.9, 10, 19.9, 20)] == [
        False,
        False,
        True,
        True,
        False,
    ]
    values = maxi_sim.drift_values(8)
    assert values["valve_open"] is False
    assert values["shutter_open"] is True
