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

### Requirement: Differential pump stage color
The `DIFFPUMP` fill SHALL be green for pressure <= 1e-7, yellow for 1e-7 < pressure <= 1e-6, red for 1e-6 < pressure <= 700, and gray for pressure > 700. Its outline stays as in the drawing.

#### Scenario: Pump at base pressure
- **WHEN** the differential pump stage pressure is 8e-9
- **THEN** `DIFFPUMP` is green

#### Scenario: Pump on a limit
- **WHEN** the differential pump stage pressure is exactly 1e-7
- **THEN** `DIFFPUMP` is green

#### Scenario: Pump pressure rising
- **WHEN** the differential pump stage pressure is 5e-7
- **THEN** `DIFFPUMP` is yellow

#### Scenario: Pump at rough vacuum
- **WHEN** the differential pump stage pressure is 1e-2
- **THEN** `DIFFPUMP` is red

#### Scenario: Pump vented
- **WHEN** the differential pump stage pressure is 1013
- **THEN** `DIFFPUMP` is gray

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

#### Scenario: Differential pump stage invalid
- **WHEN** the differential pump stage pressure has INVALID quality
- **THEN** `DIFFPUMP` is gray with purple hatching inside its rectangle

### Requirement: Unknown look of states
When the value of the valve or the shutter is unknown, it SHALL be drawn in gray (the valve with a gray body, the shutter with a gray frame), without gate or blades, with a large `?` in the body and no state word.

#### Scenario: Valve disconnected while open
- **WHEN** the valve channel disconnects while the valve shows OPEN
- **THEN** the valve shows a gray body with `?`, and neither gate nor the word `OPEN`

#### Scenario: Shutter invalid
- **WHEN** the shutter channel has INVALID quality
- **THEN** the shutter shows a gray frame with `?`, without blades and without a word

#### Scenario: Recovery
- **WHEN** the valve channel reconnects with value 0
- **THEN** the `?` is removed and the valve shows CLOSED

### Requirement: State selection
A state SHALL map each known value to one look of its drawing: body colour, gate or blade position, and state word. Exactly one look is shown at a time. The state words are plain text in one neutral colour, the same for every state. State drawings do not use hatching.

#### Scenario: Only one asset visible
- **WHEN** the shutter value changes from True to False
- **THEN** the shutter shows only its CLOSED look, with the word `CLOSED`, and nothing of its OPEN or unknown look

#### Scenario: Neutral words
- **WHEN** the valve shows OPEN and the shutter shows CLOSED
- **THEN** the words `OPEN` and `CLOSED` have the same colour

### Requirement: Valve state
The valve SHALL show its state from an integer channel: 0 CLOSED (red body, gate fully closed, word `CLOSED`), 1 OPEN (green body, gate open, word `OPEN`), 2 MOVING (amber body, upper half of the gate closed, word `MOVING`). Any other integer, like an unknown value, shows the unknown look.

#### Scenario: Valve closed
- **WHEN** the valve channel is 0
- **THEN** the valve body is red, the gate is fully closed and the word is `CLOSED`

#### Scenario: Valve open
- **WHEN** the valve channel is 1
- **THEN** the valve body is green, the gate is open and the word is `OPEN`

#### Scenario: Valve moving
- **WHEN** the valve channel is 2
- **THEN** the valve body is amber, the upper half of the gate is closed and the word is `MOVING`

#### Scenario: Value out of range
- **WHEN** the valve channel is 5 or -1
- **THEN** the valve shows the unknown look: a gray body with `?`, no gate and no word

#### Scenario: Valve unknown
- **WHEN** the valve channel is disconnected
- **THEN** the valve shows the unknown look

### Requirement: Shutter state
The shutter SHALL show OPEN (blades open, word `OPEN`) when its boolean channel is True, CLOSED (blade closed, word `CLOSED`) when it is False, and the unknown look when it is unknown.

#### Scenario: Shutter closed
- **WHEN** the shutter channel is False
- **THEN** the shutter blade is closed and the word is `CLOSED`

#### Scenario: Shutter unknown
- **WHEN** the shutter channel has INVALID quality
- **THEN** the shutter shows the unknown look

### Requirement: Beam path
The panel SHALL always draw the nominal beam path as a thin, dim, dashed line from the entry at the beamline to the detector, with an arrow for the beam direction, on top of the valve and the shutter. The beam path does not change with any value.

#### Scenario: Beam on the diode
- **WHEN** the valve and the shutter are open
- **THEN** only the dashed beam path and the arrow are drawn, with no solid beam

#### Scenario: Shutter closed
- **WHEN** the valve is open and the shutter is closed
- **THEN** no stop mark is drawn, and the dashed beam path continues to the detector

#### Scenario: Valve closed
- **WHEN** the valve is closed
- **THEN** the dashed beam path and the arrow are drawn as when it is open, across the valve body

#### Scenario: Channels disconnected
- **WHEN** the valve and shutter channels are disconnected
- **THEN** the dashed beam path and the arrow are unchanged

### Requirement: Initial state
At startup, before any value arrives, every colour and state SHALL show its unknown look.

#### Scenario: SVG saved with an asset visible
- **WHEN** `valve.ui` was saved with the word `OPEN` visible, and the valve channel has sent no value yet
- **THEN** the valve shows only the unknown look

### Requirement: Colour and state channels
The colours and states SHALL read the same configured signals as the value labels: the chamber colour the chamber pressure, the differential pump stage colour the differential pump stage pressure, the detector colour the detector temperature, the valve state `valve_state` and the shutter state `shutter_open`.

#### Scenario: Channel from configuration
- **WHEN** the configuration sets the signal `maxi_vac_pressure` to `tango://maxi-ctrl:10000/maxi/vac/gauge1/pressure`
- **THEN** both the chamber pressure label and the `MAXICHAMBER` colour use that attribute

#### Scenario: Differential pump stage channel
- **WHEN** the configuration sets the signal `diff_vac_pressure` to an address
- **THEN** the differential pump stage pressure label, its plot and the `DIFFPUMP` colour use that address
