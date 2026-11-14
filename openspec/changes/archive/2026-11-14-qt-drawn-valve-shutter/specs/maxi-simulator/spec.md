# Spec Delta

## MODIFIED Requirements

### Requirement: Simulated attributes
The simulator SHALL provide one Tango device, `maxi/sim/1`, with an attribute for every value slot, plot and rule channel of the MAXI panel. Pressures and other numeric slots are float attributes with unit and format set; status, mode and polarization slots are strings; the valve state `valve_state` is an integer (0 closed, 1 open, 2 moving); the shutter `shutter_open` is a boolean.

#### Scenario: Pressure attribute
- **WHEN** a client reads the chamber pressure attribute of `maxi/sim/1`
- **THEN** it gets a float with unit `mbar` and format `%.2e`

#### Scenario: Valve attribute
- **WHEN** a client reads `valve_state` of `maxi/sim/1`
- **THEN** it gets an integer value, initially 0

#### Scenario: Shutter attribute
- **WHEN** a client reads `shutter_open` of `maxi/sim/1`
- **THEN** it gets a `DevBoolean` value

### Requirement: Drift mode
With `--drift`, the simulator SHALL change its values by itself, so that all colors and states appear without user action: the chamber pressure cycles logarithmically between 1e-7 and 1000 mbar, the differential pump stage pressure cycles logarithmically between 1e-8 and 1000 mbar, the detector temperature cycles between -40 and 30, the valve repeats CLOSED, MOVING, OPEN, MOVING, and the shutter toggles every few seconds. Without `--drift`, values only change when written.

#### Scenario: Drift shows every chamber color
- **WHEN** the simulator runs with `--drift` for one full pressure cycle
- **THEN** the chamber pressure passes through values <= 5e-6, between 5e-6 and 700, and above 700

#### Scenario: Drift shows every differential pump stage color
- **WHEN** the simulator runs with `--drift` for one full differential pump stage cycle
- **THEN** the differential pump stage pressure passes through values <= 1e-7, between 1e-7 and 1e-6, between 1e-6 and 700, and above 700

#### Scenario: Drift shows every valve state
- **WHEN** the simulator runs with `--drift` for one full valve cycle
- **THEN** `valve_state` takes the values 0, 2, 1, 2 in this order, and a MOVING phase is shorter than a CLOSED or OPEN phase

#### Scenario: No drift
- **WHEN** the simulator runs without `--drift` and nothing is written
- **THEN** all values stay at their initial values
