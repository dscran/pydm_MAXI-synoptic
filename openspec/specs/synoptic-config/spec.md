# synoptic-config Specification

## Purpose

Defines the YAML configuration that connects the synoptic SVG to Tango attributes, and how that
configuration is validated against the SVG when the panel starts.

## Requirements

### Requirement: Configuration file location
The panel SHALL read its configuration from `maxi_synoptic.yaml` next to the display file, unless the PyDM macro `config` names another file. A relative path in the macro is resolved against the display file's directory.

#### Scenario: Default configuration file
- **WHEN** the panel is started without a `config` macro
- **THEN** it reads `maxi_synoptic.yaml` from the directory of the display file

#### Scenario: Configuration file from macro
- **WHEN** the panel is started with macro `config=other.yaml`
- **THEN** it reads `other.yaml` from the directory of the display file

### Requirement: Top-level sections
The configuration SHALL be a YAML mapping with the optional sections `defaults`, `values`, `plots` and `extra_channels`. A missing section is the same as an empty one. Any other top-level key is an error.

#### Scenario: Unknown top-level key
- **WHEN** the configuration contains a top-level key `value` (typo of `values`)
- **THEN** startup fails with an error naming the key `value`

#### Scenario: Missing section
- **WHEN** the configuration has no `plots` section
- **THEN** the panel starts and shows no plots

### Requirement: Value entries
Each entry in `values` SHALL map an SVG element id to a mapping with a required `source` and an optional `format`. Any other key is an error.

#### Scenario: Value entry without source
- **WHEN** a `values` entry has only `format: "%.2e"`
- **THEN** startup fails with an error naming the entry and the missing `source`

### Requirement: Value format
`format` SHALL be a printf-style format string with a leading `%`, as in the Tango attribute `format` property. When given, it overrides the Tango format. When it is missing, the Tango format of the attribute is used.

#### Scenario: Format override
- **WHEN** a value entry has `format: "%.2e"` and the attribute value is 0.000012345
- **THEN** the label shows `1.23e-05`

#### Scenario: Tango format used
- **WHEN** a value entry has no `format` and the attribute's Tango format is `%6.3f`
- **THEN** the label shows the value with 3 decimal places

#### Scenario: Invalid format
- **WHEN** a value entry has `format: "6.3f"` (no leading `%`)
- **THEN** startup fails with an error naming the entry and the format

### Requirement: Plot entries
Each entry in `plots` SHALL map an SVG element id to a mapping with a required `source` and `refresh_period` (seconds, > 0), and an optional `log_y` (boolean, default false), `time_span` (seconds, > 0, default 600) and `y_range` (a list `[lowest, highest]` of two numbers with lowest < highest, both > 0 when `log_y` is true). Without `y_range`, the y-axis follows the data. Any other key is an error.

#### Scenario: Complete plot entry
- **WHEN** a plot entry has `source`, `refresh_period: 1.0`, `log_y: true` and `time_span: 3600`
- **THEN** the plot adds a point every 1 s, shows the last 3600 s, and uses a logarithmic y-axis

#### Scenario: Default plot options
- **WHEN** a plot entry has only `source` and `refresh_period`
- **THEN** the plot shows the last 600 s on a linear y-axis

#### Scenario: Fixed y-axis
- **WHEN** a plot entry has `log_y: true` and `y_range: [1.0e-9, 1.0e+3]`
- **THEN** the y-axis always shows 1e-9 to 1e3, whatever the values are

#### Scenario: Invalid y-range
- **WHEN** a plot entry has `y_range: [5, 2]`, or `log_y: true` with `y_range: [0, 10]`
- **THEN** startup fails with an error naming the entry and `y_range`

#### Scenario: Non-positive refresh period
- **WHEN** a plot entry has `refresh_period: 0`
- **THEN** startup fails with an error naming the entry and `refresh_period`

### Requirement: Extra channels
Each entry in `extra_channels` SHALL map a channel name to a Tango address string. These channels are only used by the color and state rules. Entries in `values` and `plots` never refer to them.

#### Scenario: Extra channel entry
- **WHEN** `extra_channels` contains `valve_open: maxi/vac/valve1/is_open`
- **THEN** a rule that uses channel `valve_open` receives the values of that attribute

### Requirement: Tango address resolution
A `source` or extra channel address that starts with `tango://` SHALL be used as is. Any other address SHALL be prefixed with `tango://`, and with `defaults.tango_host` and a `/` when that is set. Without `tango_host`, the Tango database from the `TANGO_HOST` environment variable is used.

#### Scenario: Address with tango_host default
- **WHEN** `defaults.tango_host` is `maxi-ctrl:10000` and a source is `maxi/vac/gauge1/pressure`
- **THEN** the channel address is `tango://maxi-ctrl:10000/maxi/vac/gauge1/pressure`

#### Scenario: Address without tango_host
- **WHEN** `defaults.tango_host` is not set and a source is `maxi/vac/gauge1/pressure`
- **THEN** the channel address is `tango://maxi/vac/gauge1/pressure`

#### Scenario: Full address
- **WHEN** a source is `tango://other:10000/a/b/c/attr`
- **THEN** that address is used unchanged, whatever `defaults.tango_host` is

### Requirement: Tango poll period default
`defaults.tango_poll_period` (seconds, > 0) SHALL set the Tango plugin poll period, unless the `PYDM_TANGO_POLL_PERIOD` environment variable is already set. The environment variable wins. The panel logs which poll period is used.

#### Scenario: Poll period from YAML
- **WHEN** `tango_poll_period: 0.5` is set and `PYDM_TANGO_POLL_PERIOD` is not set
- **THEN** attributes without change events are polled every 500 ms

#### Scenario: Environment variable wins
- **WHEN** `tango_poll_period: 0.5` is set and `PYDM_TANGO_POLL_PERIOD=2000`
- **THEN** attributes without change events are polled every 2000 ms, and the log says the YAML value is ignored

#### Scenario: Plugin already loaded
- **WHEN** `tango_poll_period` is set but the Tango plugin was already loaded before the panel started
- **THEN** the panel logs a warning that `tango_poll_period` has no effect

### Requirement: Plot redraw rate default
`defaults.max_redraw_rate` (whole number of redraws per second, > 0) SHALL set the `maxRedrawRate` of every time plot. Without it, PyDM's default of 1 per second is kept.

#### Scenario: Redraw rate from YAML
- **WHEN** `max_redraw_rate: 5` is set
- **THEN** every plot is redrawn at most 5 times per second

#### Scenario: Invalid redraw rate
- **WHEN** `max_redraw_rate: 0` is set
- **THEN** startup fails with an error naming `max_redraw_rate`

### Requirement: Validation errors stop startup
At startup the panel SHALL check the configuration against the SVG. On any error, the panel SHALL NOT start, and it SHALL report every error found, not only the first. Errors are: invalid YAML, schema errors, an id in `values` or `plots` that is not in the SVG, and an id that is in both `values` and `plots`.

#### Scenario: Id not in SVG
- **WHEN** `values` contains `MAXI_VAC_presure_value` and the SVG has no element with that id
- **THEN** startup fails with an error saying there is no SVG element with id `MAXI_VAC_presure_value`

#### Scenario: Id in values and plots
- **WHEN** `MAXI_VAC_plot` is in both `values` and `plots`
- **THEN** startup fails with an error naming `MAXI_VAC_plot`

#### Scenario: Several errors
- **WHEN** the configuration has two unknown ids and one missing `source`
- **THEN** all three errors are reported together

#### Scenario: Unquoted format
- **WHEN** the YAML contains `format: %6.3f` without quotes
- **THEN** startup fails with an error giving the line, and saying that values starting with `%` must be quoted

### Requirement: Validation warnings
The panel SHALL log a warning, and still start, for each SVG element whose id ends in `_value` or `_plot` that is not configured (except `DATETIME_value`), and for each `extra_channels` entry that no rule uses.

#### Scenario: Unconfigured slot
- **WHEN** the SVG has `DIODE_encoder_value` and the configuration does not list it
- **THEN** the panel starts and logs a warning naming `DIODE_encoder_value`

#### Scenario: Unused extra channel
- **WHEN** `extra_channels` has `spare_gauge` and no rule uses it
- **THEN** the panel starts and logs a warning naming `spare_gauge`
