"""Tango device that simulates the MAXI attributes for the synoptic panel. It needs no Tango database.

    maxi-synoptic-sim [--port 45678] [--drift]

Clients read `tango://localhost:<port>/maxi/sim/1/<attribute>#dbase=no`.
"""

from __future__ import annotations

import argparse
import math
import signal
import threading
import time
from dataclasses import dataclass
from typing import Any

import tango
from tango.server import Device, attribute, command, device_property
from tango.test_context import DeviceTestContext

DEVICE_NAME = "maxi/sim/1"
DEFAULT_PORT = 45678

PRESSURE = {"unit": "mbar", "format": "%.2e"}
TEMPERATURE = {"unit": "°C", "format": "%.1f"}

DRIFT_TICK_SECONDS = 0.5
PRESSURE_RANGE = (1e-7, 1000.0)
PRESSURE_PERIOD_SECONDS = 60.0
TEMPERATURE_RANGE = (-40.0, 30.0)
TEMPERATURE_PERIOD_SECONDS = 40.0
VALVE_TOGGLE_SECONDS = 10.0
SHUTTER_TOGGLE_SECONDS = 7.0


@dataclass(frozen=True)
class SimAttribute:
    name: str
    initial: Any
    unit: str = ""
    format: str = ""

    @property
    def dtype(self) -> type:
        return type(self.initial)


ATTRIBUTES = (
    SimAttribute("diode_current", 1.5e-9, "A", "%.3e"),
    SimAttribute("diode_amplification", 1e6, "V/A", "%.0e"),
    SimAttribute("diode_encoder", 12.5, "mm", "%.3f"),
    SimAttribute("maxi_vac_pressure", 2e-7, **PRESSURE),
    SimAttribute("maxi_vac_roughing_pressure", 3e-2, **PRESSURE),
    SimAttribute("shutter_vac_pressure", 5e-8, **PRESSURE),
    SimAttribute("shutter_vac_roughing_pressure", 2e-2, **PRESSURE),
    SimAttribute("diff_vac_pressure", 8e-9, **PRESSURE),
    SimAttribute("diff_vac_roughing_pressure", 1e-2, **PRESSURE),
    SimAttribute("beamline_status", "ON"),
    SimAttribute("beamline_energy", 778.0, "eV", "%.2f"),
    SimAttribute("beamline_polarization", "circular +"),
    SimAttribute("beamline_exit_slit", 50.0, "µm", "%.1f"),
    SimAttribute("detector_status", "IDLE"),
    SimAttribute("detector_temp", -40.0, **TEMPERATURE),
    SimAttribute("detector_temp_setpoint", -40.0, **TEMPERATURE),
    SimAttribute("magnet_current_amplitude", 2.0, "A", "%.3f"),
    SimAttribute("magnet_current_angle", 45.0, "deg", "%.1f"),
    SimAttribute("shutter_panel_mode", "manual"),
    SimAttribute("shutter_panel_status", "closed"),
    SimAttribute("valve_open", False),
    SimAttribute("shutter_open", False),
)
ATTRIBUTE_NAMES = tuple(spec.name for spec in ATTRIBUTES)


def triangle(elapsed: float, period: float) -> float:
    """A triangle wave that goes from 0 up to 1 and back to 0 once per period."""
    phase = (elapsed % period) / period
    return 1 - abs(2 * phase - 1)


def drift_pressure(elapsed: float) -> float:
    """The chamber pressure in drift mode: a triangle wave on a logarithmic scale."""
    low, high = (math.log10(limit) for limit in PRESSURE_RANGE)
    return 10 ** (low + (high - low) * triangle(elapsed, PRESSURE_PERIOD_SECONDS))


def drift_temperature(elapsed: float) -> float:
    low, high = TEMPERATURE_RANGE
    return low + (high - low) * triangle(elapsed, TEMPERATURE_PERIOD_SECONDS)


def drift_toggle(elapsed: float, interval: float) -> bool:
    """A state that changes every `interval` seconds, starting with False."""
    return int(elapsed // interval) % 2 == 1


def drift_values(elapsed: float) -> dict[str, Any]:
    """The values of all drifting attributes after `elapsed` seconds."""
    return {
        "maxi_vac_pressure": drift_pressure(elapsed),
        "detector_temp": drift_temperature(elapsed),
        "valve_open": drift_toggle(elapsed, VALVE_TOGGLE_SECONDS),
        "shutter_open": drift_toggle(elapsed, SHUTTER_TOGGLE_SECONDS),
    }


def attribute_address(host_port: str, attribute_name: str) -> str:
    return f"tango://{host_port}/{DEVICE_NAME}/{attribute_name}#dbase=no"


def panel_signals(host_port: str) -> dict[str, str]:
    """The panel configuration for a simulator at `host_port`: every signal of the panel is an attribute."""
    return {name: attribute_address(host_port, name) for name in ATTRIBUTE_NAMES}


class MaxiSim(Device):
    """Writable attributes for every signal of the MAXI synoptic."""

    Drift = device_property(dtype=bool, default_value=False, doc="Change values over time")

    def init_device(self):
        super().init_device()
        self._values = {spec.name: spec.initial for spec in ATTRIBUTES}
        self._invalid = set()
        self._stop_drift = threading.Event()
        self._drift_thread = None
        self.set_state(tango.DevState.ON)

    def initialize_dynamic_attributes(self):
        for spec in ATTRIBUTES:
            self.add_attribute(self._make_attribute(spec))
            # Pushed by the code and not checked against a threshold, so that clients need no polling
            self.set_change_event(spec.name, True, False)
        if self.Drift:
            self._drift_thread = threading.Thread(target=self._drift, daemon=True)
            self._drift_thread.start()

    def delete_device(self):
        self._stop_drift.set()
        if self._drift_thread is not None:
            self._drift_thread.join()

    def _make_attribute(self, spec):
        settings = {"unit": spec.unit, "format": spec.format}
        given_settings = {key: text for key, text in settings.items() if text}
        return attribute(
            name=spec.name,
            dtype=spec.dtype,
            access=tango.AttrWriteType.READ_WRITE,
            fget=self.read_value,
            fset=self.write_value,
            **given_settings,
        )

    def read_value(self, attr):
        name = attr.get_name()
        return self._values[name], time.time(), self._quality(name)

    def write_value(self, attr):
        self._set_value(attr.get_name(), attr.get_write_value())

    @command(dtype_in=str, doc_in="Attribute name")
    def SetInvalid(self, name):
        """Make an attribute report INVALID quality."""
        self._check_name(name, "SetInvalid")
        self._invalid.add(name)
        self._push(name)

    @command(dtype_in=str, doc_in="Attribute name")
    def ClearInvalid(self, name):
        """Make an attribute report VALID quality again."""
        self._check_name(name, "ClearInvalid")
        self._invalid.discard(name)
        self._push(name)

    def _check_name(self, name, origin):
        if name not in self._values:
            tango.Except.throw_exception("MaxiSim_UnknownAttribute", f"no attribute named '{name}'", origin)

    def _quality(self, name):
        if name in self._invalid:
            return tango.AttrQuality.ATTR_INVALID
        return tango.AttrQuality.ATTR_VALID

    def _set_value(self, name, value):
        self._values[name] = value
        self._push(name)

    def _push(self, name):
        self.push_change_event(name, self._values[name], time.time(), self._quality(name))

    def _drift(self):
        # Tango requires this for threads that it did not create itself
        with tango.EnsureOmniThread():
            start = time.monotonic()
            while not self._stop_drift.wait(DRIFT_TICK_SECONDS):
                for name, value in drift_values(time.monotonic() - start).items():
                    self._set_value(name, value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated MAXI device for the synoptic panel")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port of the device server")
    parser.add_argument("--drift", action="store_true", help="change values over time")
    args = parser.parse_args()

    context = DeviceTestContext(
        MaxiSim, device_name=DEVICE_NAME, port=args.port, properties={"Drift": args.drift}, process=True
    )
    # Stop on `kill` like on Ctrl+C, so that the device server process never stays behind
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    with context:
        address = f"tango://localhost:{args.port}/{DEVICE_NAME}#dbase=no"
        print(f"MaxiSim is running: {address}  (Ctrl+C to stop)", flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("\nStopping MaxiSim", flush=True)


if __name__ == "__main__":
    main()
