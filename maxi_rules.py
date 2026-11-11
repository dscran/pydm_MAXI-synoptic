"""Color and state rules of the MAXI synoptic. Their channels are named in `extra_channels` of the YAML."""

from synoptic.rules import UNKNOWN_COLOR, bands, color_rule, state_rule

# The palette of MAXI_synoptic_v2.svg
GREEN = "#4fae7b"
YELLOW = "#d6a544"
BLUE = "#4b8fc4"
GRAY = UNKNOWN_COLOR

HIGH_VACUUM_MAX_PRESSURE = 5e-6
ROUGH_VACUUM_MAX_PRESSURE = 700
COLD_MAX_TEMPERATURE = 15


@color_rule(channel="chamber_pressure", target="MAXICHAMBER")
def chamber(pressure):
    limits = [(HIGH_VACUUM_MAX_PRESSURE, GREEN), (ROUGH_VACUUM_MAX_PRESSURE, YELLOW)]
    return bands(pressure, limits, above=GRAY)


@color_rule(channel="detector_temperature", target="DETECTOR")
def detector(temperature):
    return bands(temperature, [(COLD_MAX_TEMPERATURE, BLUE)], above=GRAY)


@state_rule(channel="valve_open", assets={"VALVE_OPEN", "VALVE_CLOSED"}, unknown="VALVE_UNKNOWN")
def valve(is_open):
    if is_open:
        return "VALVE_OPEN"
    return "VALVE_CLOSED"


@state_rule(channel="shutter_open", assets={"SHUTTER_OPEN", "SHUTTER_CLOSED"}, unknown="SHUTTER_UNKNOWN")
def shutter(is_open):
    if is_open:
        return "SHUTTER_OPEN"
    return "SHUTTER_CLOSED"
