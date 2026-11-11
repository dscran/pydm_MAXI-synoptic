# maxi-simulator Specification

## Purpose

Provides a Tango device that simulates the MAXI attributes, so that the synoptic panel can be developed,
tested and demonstrated without the real control system or a Tango database.

## Requirements

### Requirement: Simulated attributes
The simulator SHALL provide one Tango device, `maxi/sim/1`, with an attribute for every value slot, plot and rule channel of the MAXI panel. Pressures and other numeric slots are float attributes with unit and format set; status, mode and polarization slots are strings; valve and shutter are booleans.

#### Scenario: Pressure attribute
- **WHEN** a client reads the chamber pressure attribute of `maxi/sim/1`
- **THEN** it gets a float with unit `mbar` and format `%.2e`

#### Scenario: Valve attribute
- **WHEN** a client reads the valve attribute of `maxi/sim/1`
- **THEN** it gets a `DevBoolean` value

### Requirement: Settable values with change events
Every simulated attribute SHALL be writable. Writing a value sets the read value and pushes a change event, so clients receive it without polling.

#### Scenario: Write pressure
- **WHEN** a test writes 1e-3 to the chamber pressure attribute
- **THEN** a client subscribed to change events receives 1e-3

### Requirement: Quality control
The simulator SHALL offer the commands `SetInvalid(name)` and `ClearInvalid(name)`. `SetInvalid` makes the named attribute report INVALID quality and pushes a change event; `ClearInvalid` restores VALID quality. An unknown name is an error.

#### Scenario: Invalid shutter
- **WHEN** a test calls `SetInvalid("shutter_open")`
- **THEN** clients of `shutter_open` receive INVALID quality

#### Scenario: Unknown attribute name
- **WHEN** a test calls `SetInvalid("no_such_attr")`
- **THEN** the command fails with a Tango error naming `no_such_attr`

### Requirement: Runs without a Tango database
The simulator SHALL run without a Tango database, from the command line on a fixed port (default 45678, set with `--port`), and inside tests through a Tango test context. Clients address it as `tango://<host>:<port>/maxi/sim/1/<attribute>#dbase=no`. On the command line it is started with the installed command `maxi-synoptic-sim`.

#### Scenario: Manual start
- **WHEN** a user runs `maxi-synoptic-sim --port 45678`
- **THEN** `tango://localhost:45678/maxi/sim/1/<attribute>#dbase=no` can be read until the simulator is stopped

### Requirement: Drift mode
With `--drift`, the simulator SHALL change its values by itself, so that all colors and states appear without user action: the chamber pressure cycles logarithmically between 1e-7 and 1000 mbar, the detector temperature cycles between -40 and 30, and the valve and shutter toggle at different intervals of a few seconds. Without `--drift`, values only change when written.

#### Scenario: Drift shows every chamber color
- **WHEN** the simulator runs with `--drift` for one full pressure cycle
- **THEN** the chamber pressure passes through values <= 5e-6, between 5e-6 and 700, and above 700

#### Scenario: No drift
- **WHEN** the simulator runs without `--drift` and nothing is written
- **THEN** all values stay at their initial values

### Requirement: Simulator configuration
The installed package SHALL contain `sim.json`, the bundled configuration named `sim`, which connects every signal of the panel to the simulator on its default port. It passes the configuration check of the `maxi-synoptic` command with no errors and no warnings.

#### Scenario: Panel on the simulator
- **WHEN** the simulator runs with default settings and the panel is started with `maxi-synoptic --config sim`
- **THEN** the panel starts without configuration errors or warnings, and every value slot shows a value
