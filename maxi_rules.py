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


# The beam comes in at the beamline and ends at the diode. The valve and the shutter can stop it.
# In the SVG, the beam after the shutter lies inside the group of the beam after the valve, so it is
# only drawn when the valve lets the beam pass as well.


# A valve in an unknown state is drawn as letting the beam pass: assuming beam is the safer mistake.
@state_rule(channel="valve_open", assets={"BEAM_VALVE_OPEN", "BEAM_VALVE_CLOSED"}, unknown="BEAM_VALVE_OPEN")
def beam_after_valve(is_open):
    if is_open:
        return "BEAM_VALVE_OPEN"
    return "BEAM_VALVE_CLOSED"


@state_rule(
    channel="shutter_open",
    assets={"BEAM_SHUTTER_OPEN", "BEAM_SHUTTER_CLOSED"},
    unknown="BEAM_SHUTTER_UNKNOWN",
)
def beam_after_shutter(is_open):
    if is_open:
        return "BEAM_SHUTTER_OPEN"
    return "BEAM_SHUTTER_CLOSED"
