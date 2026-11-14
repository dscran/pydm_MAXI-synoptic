# synoptic-config Specification

## Purpose

Defines the configuration that connects the panel to Tango: a JSON file that maps each signal of
the panel to a channel address, and how the `maxi-synoptic` command selects and checks it before PyDM
starts.

## Requirements

### Requirement: Configuration selection
The panel SHALL take its configuration from the bundled default file `default.json`, unless the `maxi-synoptic` option `--config` names another configuration. A value without a `/` and without a `.json` suffix is the name of a bundled configuration (`default` or `sim`). Any other value is a file path; a relative path is resolved against the current directory. An unknown bundled name is a configuration error that lists the known names.

#### Scenario: Default configuration file
- **WHEN** the panel is started with `maxi-synoptic` and no `--config`
- **THEN** it uses the bundled `default.json`

#### Scenario: Bundled simulator configuration
- **WHEN** the panel is started with `maxi-synoptic --config sim`
- **THEN** it uses the bundled `sim.json`

#### Scenario: Configuration file from option
- **WHEN** the panel is started from directory `/home/op` with `--config other.json`
- **THEN** it uses `/home/op/other.json`

#### Scenario: Absolute path
- **WHEN** the panel is started with `--config /etc/maxi/panel.json`
- **THEN** it uses `/etc/maxi/panel.json`

#### Scenario: Unknown bundled name
- **WHEN** the panel is started with `--config simulator`
- **THEN** it does not start and reports that `simulator` is not a bundled configuration, naming `default` and `sim`

### Requirement: Configuration check
Before PyDM starts, the `maxi-synoptic` command SHALL check the configuration file. If the file is not valid JSON, is not a mapping of signal names to strings, or lacks a signal that the panel uses, the panel SHALL NOT start, and every error found SHALL be reported, not only the first. Addresses are not checked.

#### Scenario: Missing signal
- **WHEN** the configuration has no `shutter_open`
- **THEN** startup fails with an error naming `shutter_open`

#### Scenario: Several errors
- **WHEN** the configuration lacks two signals and gives a number instead of a string for a third
- **THEN** all three errors are reported together

#### Scenario: Invalid JSON
- **WHEN** the configuration file has a trailing comma
- **THEN** startup fails with an error naming the file and the line

#### Scenario: Wrong address
- **WHEN** a signal is set to an address that does not exist
- **THEN** the panel starts, and the widgets of that signal show PyDM's disconnected look

### Requirement: Signal configuration
The configuration SHALL be a JSON object that maps each signal name of the panel to the full channel address of its Tango attribute, for example `"maxi_vac_pressure": "tango://maxi-ctrl:10000/maxi/vac/chamber_gauge/pressure"`. The signal names are the simulator's attribute names: one per value slot, plus `valve_state` and `shutter_open`. Each address is used unchanged.

#### Scenario: Signal used by several widgets
- **WHEN** `maxi_vac_pressure` is set to an address
- **THEN** the chamber pressure label, the chamber pressure plot and the `MAXICHAMBER` colour all use that address

#### Scenario: Address without a database
- **WHEN** a signal is set to `tango://localhost:45678/maxi/sim/1/valve_state#dbase=no`
- **THEN** the panel reads that attribute from the simulator without a Tango database

#### Scenario: Old valve signal
- **WHEN** a configuration has `valve_open` but no `valve_state`
- **THEN** the panel does not start and reports that `valve_state` is missing

### Requirement: Unused signals warn
The `maxi-synoptic` command SHALL log a warning, and still start, for each signal in the configuration that the panel does not use.

#### Scenario: Extra signal
- **WHEN** the configuration has a signal `spare_gauge` that the panel does not use
- **THEN** the panel starts and logs a warning naming `spare_gauge`
