# synoptic-display Specification

## Purpose

Shows the MAXI drawing at a fixed 1920x1080 as a Qt Designer file of PyDM widgets: images exported
from the drawing, with live value labels and time plots placed on its slots.

## Requirements

### Requirement: SVG background
The panel SHALL show the MAXI drawing at a fixed size of 1920x1080 pixels, unscaled. A larger window shows the panel in its top-left corner on the panel's background colour; a smaller window shows only part of the panel. The drawing comes from `MAXI_synoptic_v2.svg`.

#### Scenario: Window with a different aspect ratio
- **WHEN** the panel is shown in a 2560x1440 window
- **THEN** the drawing is drawn at 1920x1080 in the top-left corner, not distorted and not scaled

#### Scenario: Window smaller than the panel
- **WHEN** the panel is shown in a 960x540 window
- **THEN** the drawing and all values keep their size and position, and only the top-left part of the panel is visible

### Requirement: Value overlays
The panel SHALL show a read-only value label over each value slot of the drawing (each element whose id ends in `_value`, except `DATETIME_value`), connected to the channel of that signal. The label shows the Tango unit, uses the number format given for that slot, and shows the PyDM alarm border for the attribute quality. The exception is `DIODE_amplification_value`: the device gives the exponent of the gain, so the label reads it through a `calc://` channel that computes `10**x`, and shows the result in the format `%.0e` (e.g. `1e+06`) without a unit. `SHUTTER_PANEL_mode_value` likewise reads the integer shutter mode through a `calc://` channel that shows `HW AND SW` (0), `HW OR SW` (1), `SW ONLY` (2), `HW ONLY` (3), or `UNKNOWN` for any other value.

#### Scenario: Label placement
- **WHEN** the panel runs at its fixed size
- **THEN** the label of `MAXI_VAC_pressure_value` covers the rectangle of that slot in the drawing, and shows the chamber pressure with its unit in the format `%.2e`

#### Scenario: Tango format used
- **WHEN** a slot has no format of its own and the attribute's Tango format is `%.3f`
- **THEN** the label shows the value with 3 decimal places

#### Scenario: Disconnected value
- **WHEN** the channel of a value label is disconnected
- **THEN** the label shows PyDM's disconnected style: a dashed border, with the channel address as its text

#### Scenario: Invalid value
- **WHEN** the attribute of a value label has INVALID quality
- **THEN** the label shows the INVALID alarm border and the INVALID text colour of the style sheet

### Requirement: Plot overlays
The panel SHALL show a time plot of the chamber, shutter-chamber and differential-pump-stage pressures over the plot slots `MAXI_VAC_plot`, `SHUTTER_VAC_plot` and `DIFF_VAC_plot`. Each plot adds the latest value every second, even when the value has not changed, shows the last 600 s on a logarithmic y-axis fixed at 1e-9 to 1e3, and starts empty.

#### Scenario: Slowly changing value
- **WHEN** a plotted pressure does not change for 60 s
- **THEN** the plot shows a flat line with about 60 new points over that time

#### Scenario: Fixed y-axis
- **WHEN** a plotted pressure is 1e-7
- **THEN** the y-axis still shows 1e-9 to 1e3

### Requirement: Value style sheet
The font size and text colour of the value labels SHALL come from the Qt style sheet `maxi_synoptic.qss` installed with the panel, not from the desktop theme. The `maxi-synoptic` command applies this style sheet.

#### Scenario: Font size from the style sheet
- **WHEN** `maxi_synoptic.qss` sets `font-size: 20px` for `PyDMLabel`
- **THEN** every value label shows its text 20 px high

#### Scenario: Dark desktop theme
- **WHEN** the desktop theme has light text and `maxi_synoptic.qss` sets a dark `color` for `PyDMLabel`
- **THEN** the values are shown in the dark colour of the style sheet

### Requirement: Read-only panel
No widget on the panel SHALL write to the control system.

#### Scenario: Clicking a value
- **WHEN** an operator clicks or types on a value label or plot
- **THEN** no value is written to any Tango attribute

### Requirement: Plot colours
The time plots SHALL have the dark background of their slots and light axes and curves.

#### Scenario: Dark slot
- **WHEN** the panel runs
- **THEN** each plot has the background `#15181c` and light axes and curve

### Requirement: Placeable valve and shutter
The valve and the shutter SHALL each be drawn by one reusable display that takes its channel as a parameter. The panel SHALL place each with a single widget, so that moving that widget in Qt Designer moves the whole drawing, its word and its unknown look. The drawing `MAXI_synoptic_v2.svg` SHALL contain no valve or shutter states.

#### Scenario: Valve moved in Designer
- **WHEN** the valve's widget in `maxi_synoptic.ui` is moved 100 px to the left
- **THEN** the valve body, gate, word and `?` are all drawn 100 px further left, and nothing of the valve stays at the old place

#### Scenario: Second valve
- **WHEN** a second valve widget is added with another channel
- **THEN** it shows the states of that channel, independently of the first valve

#### Scenario: Style sheet applies inside
- **WHEN** the valve channel disconnects
- **THEN** the valve inside its embedded display shows the unknown look set by `maxi_synoptic.qss`
