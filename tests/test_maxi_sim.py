"""The parts of the simulator that need no device server. The device itself is used by test_integration."""

import itertools
import json
import logging
import math

import pytest

from maxi_synoptic import cli
from maxi_synoptic import sim as maxi_sim
from maxi_synoptic.sim import ATTRIBUTES, DEFAULT_PORT


def test_sim_configuration_connects_every_signal_to_the_simulator():
    bundled = json.loads(cli.BUNDLED_CONFIGS["sim"].read_text())
    assert bundled == maxi_sim.panel_signals(f"localhost:{DEFAULT_PORT}")


def test_sim_configuration_passes_the_check(caplog):
    with caplog.at_level(logging.WARNING, logger=cli.__name__):
        signals = cli.load_config(cli.config_path("sim"))
    assert caplog.records == []
    assert set(signals) == cli.panel_signals()


def test_attribute_types():
    types = {spec.name: spec.dtype for spec in ATTRIBUTES}
    assert types["maxi_vac_pressure"] is float
    assert types["beamline_status"] is str
    assert types["valve_state"] is int and types["shutter_open"] is bool


def test_only_drifting_attributes_change():
    assert set(maxi_sim.drift_values(3)) == {
        "maxi_vac_pressure",
        "diff_vac_pressure",
        "detector_temp",
        "valve_state",
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


def test_pressure_cycle_shows_every_diffpump_color():
    ticks = int(maxi_sim.DIFF_PRESSURE_PERIOD_SECONDS / maxi_sim.DRIFT_TICK_SECONDS)
    pressures = [
        maxi_sim.drift_diff_pressure(tick * maxi_sim.DRIFT_TICK_SECONDS) for tick in range(ticks + 1)
    ]
    assert min(pressures) == pytest.approx(1e-8)
    assert max(pressures) == pytest.approx(1000)
    assert any(pressure <= 1e-7 for pressure in pressures)
    assert any(1e-7 < pressure <= 1e-6 for pressure in pressures)
    assert any(1e-6 < pressure <= 700 for pressure in pressures)
    assert any(pressure > 700 for pressure in pressures)


def test_temperature_cycle_shows_both_detector_colors():
    temperatures = [maxi_sim.drift_temperature(second) for second in range(41)]
    assert min(temperatures) == pytest.approx(-40)
    assert max(temperatures) == pytest.approx(30)


def phases(states):
    """The runs of equal states: (state, number of ticks) for each run."""
    return [(state, len(list(run))) for state, run in itertools.groupby(states)]


def test_valve_cycle_shows_every_state_in_order():
    cycle_seconds = sum(duration for _, duration in maxi_sim.VALVE_CYCLE)
    ticks = int(cycle_seconds / maxi_sim.DRIFT_TICK_SECONDS)
    states = [maxi_sim.drift_valve(tick * maxi_sim.DRIFT_TICK_SECONDS) for tick in range(ticks)]
    closed, opened, moving = maxi_sim.VALVE_CLOSED, maxi_sim.VALVE_OPEN, maxi_sim.VALVE_MOVING
    order = [state for state, _ in phases(states)]
    assert order == [closed, moving, opened, moving]
    ticks_of = [ticks for _, ticks in phases(states)]
    closed_ticks, moving_ticks, open_ticks, moving_again_ticks = ticks_of
    assert max(moving_ticks, moving_again_ticks) < min(closed_ticks, open_ticks)
    assert maxi_sim.drift_valve(cycle_seconds) == closed


def test_shutter_toggles():
    assert [maxi_sim.drift_toggle(second, 10) for second in (0, 9.9, 10, 19.9, 20)] == [
        False,
        False,
        True,
        True,
        False,
    ]
    values = maxi_sim.drift_values(8)
    assert values["valve_state"] == maxi_sim.VALVE_CLOSED
    assert values["shutter_open"] is True
