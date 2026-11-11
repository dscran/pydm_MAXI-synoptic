# Spec Delta

## ADDED Requirements

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
The configuration SHALL be a JSON object that maps each signal name of the panel to the full channel address of its Tango attribute, for example `"maxi_vac_pressure": "tango://maxi-ctrl:10000/maxi/vac/chamber_gauge/pressure"`. The signal names are the simulator's attribute names: one per value slot, plus `valve_open` and `shutter_open`. Each address is used unchanged.

#### Scenario: Signal used by several widgets
- **WHEN** `maxi_vac_pressure` is set to an address
- **THEN** the chamber pressure label, the chamber pressure plot and the `MAXICHAMBER` colour all use that address

#### Scenario: Address without a database
- **WHEN** a signal is set to `tango://localhost:45678/maxi/sim/1/valve_open#dbase=no`
- **THEN** the panel reads that attribute from the simulator without a Tango database

### Requirement: Unused signals warn
The `maxi-synoptic` command SHALL log a warning, and still start, for each signal in the configuration that the panel does not use.

#### Scenario: Extra signal
- **WHEN** the configuration has a signal `spare_gauge` that the panel does not use
- **THEN** the panel starts and logs a warning naming `spare_gauge`

## REMOVED Requirements

### Requirement: Top-level sections
**Reason**: The YAML configuration with `defaults`, `values`, `plots` and `extra_channels` is replaced by one flat JSON mapping of signals.
**Migration**: Put every `source` of `values` and every address of `extra_channels` into the JSON file under its signal name. `plots` and `defaults` have no counterpart in the file (see the other removed requirements).

### Requirement: Value entries
**Reason**: Value slots and their channels are defined in the Designer file; the configuration only names addresses.
**Migration**: Move each `source` to the JSON file under the signal name of its slot.

### Requirement: Value format
**Reason**: Number formats are settings of the labels in the Designer file.
**Migration**: The formats of the old default configuration are set in the Designer file. To change one, edit the label's display format and precision in Qt Designer.

### Requirement: Plot entries
**Reason**: The plots are defined in the Designer file, with the settings given in synoptic-display.
**Migration**: Change plot settings (period, time span, log axis, y-range) in Qt Designer.

### Requirement: Extra channels
**Reason**: Colours and states read the same signals as the labels (see synoptic-rules).
**Migration**: Move `chamber_pressure`, `detector_temperature`, `valve_open` and `shutter_open` to the signals `maxi_vac_pressure`, `detector_temp`, `valve_open` and `shutter_open`.

### Requirement: Tango address resolution
**Reason**: Every address in the JSON file is a full channel address. There is no `tango_host` default.
**Migration**: Write each address in full, starting with `tango://<host>:<port>/`.

### Requirement: Tango poll period default
**Reason**: There is no `defaults` section. The Tango plugin reads its poll period from its own environment variable.
**Migration**: Set `PYDM_TANGO_POLL_PERIOD` (milliseconds) in the environment before starting the panel.

### Requirement: Plot redraw rate default
**Reason**: The redraw rate is a setting of each plot in the Designer file.
**Migration**: Change `maxRedrawRate` of the plots in Qt Designer.

### Requirement: Validation warnings
**Reason**: Without the YAML, there are no unconfigured slots or unused extra channels to report. Unused signals are reported instead (see "Unused signals warn").
**Migration**: None.

### Requirement: Configuration file location
**Reason**: The YAML file chosen by the PyDM macro `config` is replaced by a JSON file chosen with the command option `--config` (see "Configuration selection").
**Migration**: Use `maxi-synoptic --config <name or path>`; `config=sim` becomes `--config sim`, and a YAML file must be rewritten as JSON.

### Requirement: Validation errors stop startup
**Reason**: There are no SVG ids, value or plot entries or printf formats in the configuration to check. The command checks the JSON file instead (see "Configuration check").
**Migration**: None.
