# synoptic-rules Specification

## Purpose

Changes the look of the drawing from control system values: PyDM rules colour the chamber and the
detector, and PyDM symbols show the state drawings of the valve, the shutter and the beam. Unknown
values have a defined look, set by the style sheet.

## Requirements

### Requirement: Unknown values
A colour or state SHALL be unknown when its channel is disconnected, the attribute quality is INVALID, or no value has arrived yet. ALARM and WARNING quality do not make a value unknown.

#### Scenario: Before the first value
- **WHEN** the panel has just started and the chamber pressure channel has not connected yet
- **THEN** `MAXICHAMBER` shows its unknown look

#### Scenario: Alarm quality
- **WHEN** the chamber pressure is 1e-6 with ALARM quality
- **THEN** `MAXICHAMBER` is green, as for VALID quality

#### Scenario: Invalid quality
- **WHEN** the detector temperature has INVALID quality
- **THEN** `DETECTOR` shows its unknown look

### Requirement: Color threshold bands
A color rule SHALL compare its value against an ordered list of upper limits. The first band with `value <= upper` gives the color; a value above every limit gets the rule's last color. Units are not checked.

#### Scenario: Value equal to a limit
- **WHEN** the chamber pressure is exactly 700
- **THEN** `MAXICHAMBER` is yellow

### Requirement: Chamber color
The `MAXICHAMBER` fill SHALL be green for pressure <= 5e-6, yellow for 5e-6 < pressure <= 700, and gray for pressure > 700.

#### Scenario: High vacuum
- **WHEN** the chamber pressure is 3e-7
- **THEN** `MAXICHAMBER` is green

#### Scenario: Intermediate pressure
- **WHEN** the chamber pressure is 1e-3
- **THEN** `MAXICHAMBER` is yellow

#### Scenario: Vented
- **WHEN** the chamber pressure is 1013
- **THEN** `MAXICHAMBER` is gray

### Requirement: Detector color
The `DETECTOR` fill SHALL be blue for temperature <= 15 and gray for temperature > 15.

#### Scenario: Cold detector
- **WHEN** the detector temperature is -40
- **THEN** `DETECTOR` is blue

#### Scenario: Warm detector
- **WHEN** the detector temperature is 22
- **THEN** `DETECTOR` is gray

### Requirement: Unknown look of color rules
When the value of a colour is unknown, its target element SHALL be drawn with a gray fill, covered by purple diagonal hatching that follows the element's exact shape, and nothing outside it. The detector has square corners.

#### Scenario: Disconnected gauge
- **WHEN** the chamber pressure channel disconnects while `MAXICHAMBER` is green
- **THEN** `MAXICHAMBER` turns gray with purple hatching inside its circle, and no hatching outside it

#### Scenario: Recovery
- **WHEN** the channel reconnects with pressure 3e-7
- **THEN** the hatching is removed and `MAXICHAMBER` is green

#### Scenario: Detector corners
- **WHEN** the detector temperature channel is disconnected
- **THEN** the hatching fills `DETECTOR` into its square corners, and no gray or blue of the drawing shows at its edges

### Requirement: State selection
A state rule SHALL map each known value to one SVG asset, and have one asset for unknown values. Exactly one of its assets is shown at a time; the others are hidden. State rules do not use hatching.

#### Scenario: Only one asset visible
- **WHEN** a state rule's value changes from True to False
- **THEN** the False asset is shown and the True and unknown assets are hidden

### Requirement: Valve state
The valve SHALL show `VALVE_OPEN` when its boolean channel is True, `VALVE_CLOSED` when it is False, and `VALVE_UNKNOWN` when it is unknown.

#### Scenario: Valve open
- **WHEN** the valve channel is True
- **THEN** only `VALVE_OPEN` is visible

#### Scenario: Valve unknown
- **WHEN** the valve channel is disconnected
- **THEN** only `VALVE_UNKNOWN` is visible

### Requirement: Shutter state
The shutter SHALL show `SHUTTER_OPEN` when its boolean channel is True, `SHUTTER_CLOSED` when it is False, and `SHUTTER_UNKNOWN` when it is unknown.

#### Scenario: Shutter closed
- **WHEN** the shutter channel is False
- **THEN** only `SHUTTER_CLOSED` is visible

#### Scenario: Shutter unknown
- **WHEN** the shutter channel has INVALID quality
- **THEN** only `SHUTTER_UNKNOWN` is visible

### Requirement: Beam path
The panel SHALL always draw the nominal beam path as a thin, dim, dashed line from the entry at the beamline to the detector. On top of it, it SHALL draw the beam itself as a solid line: from the entry to the valve, on to the shutter unless the valve is closed, and on to the diode if the shutter is open as well. A closed valve or shutter shows a stop mark where it stops the beam.

#### Scenario: Beam on the diode
- **WHEN** the valve and the shutter are open
- **THEN** a solid beam is drawn from the entry to the diode, and the dashed path continues to the detector

#### Scenario: Shutter closed
- **WHEN** the valve is open and the shutter is closed
- **THEN** the solid beam ends at the shutter with a stop mark, and only the dashed path is drawn behind it

#### Scenario: Valve closed
- **WHEN** the valve is closed and the shutter is open
- **THEN** the solid beam ends at the valve with a stop mark, and only the dashed path is drawn behind it

### Requirement: Unknown states on the beam path
A valve in an unknown state SHALL be drawn as letting the beam pass, because wrongly showing beam is the safer mistake. Behind the shutter, the beam SHALL be drawn as a stronger dashed line up to the diode when the valve or the shutter channel is disconnected. While the shutter is connected but INVALID, the beam behind it keeps its last drawing, and the shutter itself shows `SHUTTER_UNKNOWN`.

#### Scenario: Valve unknown
- **WHEN** the valve channel is disconnected and the shutter is closed
- **THEN** the solid beam is drawn through the valve up to the shutter, and the beam behind the shutter is strongly dashed

#### Scenario: Shutter unknown
- **WHEN** the valve is open and the shutter channel is disconnected
- **THEN** the beam is solid up to the shutter and strongly dashed from the shutter to the diode

#### Scenario: Shutter invalid
- **WHEN** the valve and the shutter are open and the shutter then reports INVALID quality
- **THEN** only `SHUTTER_UNKNOWN` of the shutter drawings is visible, and the beam behind the shutter is still drawn as passing

### Requirement: Initial state
At startup, before any value arrives, every rule SHALL show its unknown look, whatever visibility and colors the SVG file was saved with.

#### Scenario: SVG saved with an asset visible
- **WHEN** the SVG file was saved with `VALVE_OPEN` visible
- **THEN** after startup only `VALVE_UNKNOWN` is visible until the valve channel sends a value

### Requirement: Colour and state channels
The colours and states SHALL read the same configured signals as the value labels: the chamber colour the chamber pressure, the detector colour the detector temperature, and the valve, shutter and beam states the valve and shutter booleans.

#### Scenario: Channel from configuration
- **WHEN** the configuration sets the signal `maxi_vac_pressure` to `tango://maxi-ctrl:10000/maxi/vac/gauge1/pressure`
- **THEN** both the chamber pressure label and the `MAXICHAMBER` colour use that attribute
