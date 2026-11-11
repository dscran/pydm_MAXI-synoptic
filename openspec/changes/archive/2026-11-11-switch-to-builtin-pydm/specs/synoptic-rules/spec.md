# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Colour and state channels
The colours and states SHALL read the same configured signals as the value labels: the chamber colour the chamber pressure, the detector colour the detector temperature, and the valve, shutter and beam states the valve and shutter booleans.

#### Scenario: Channel from configuration
- **WHEN** the configuration sets the signal `maxi_vac_pressure` to `tango://maxi-ctrl:10000/maxi/vac/gauge1/pressure`
- **THEN** both the chamber pressure label and the `MAXICHAMBER` colour use that attribute

## REMOVED Requirements

### Requirement: Rules use extra channels
**Reason**: Colours and states are configured as PyDM rules and symbols in the Designer file, and read the same signals as the labels. There is no `extra_channels` section and no Python rule any more.
**Migration**: Remove `extra_channels` from the configuration. Set the signals `maxi_vac_pressure`, `detector_temp`, `valve_open` and `shutter_open` in the JSON macro file. Thresholds and colours are edited in Qt Designer, in the rules of the chamber and detector shapes.

### Requirement: Rule validation
**Reason**: There is no rule code that declares element ids, and no `extra_channels` to check. The state drawings are exported image files that ship with the panel.
**Migration**: None. A missing signal shows as disconnected (see synoptic-config).

### Requirement: Repaint rate
**Reason**: The drawing is no longer re-rendered as a whole. Each shape or symbol repaints only itself when its value changes, which costs less at 10 Hz than the throttled whole-drawing redraw did.
**Migration**: None.
