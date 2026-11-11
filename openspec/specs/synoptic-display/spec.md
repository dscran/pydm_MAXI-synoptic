# synoptic-display Specification

## Purpose

Renders the synoptic SVG as the panel background and places live value labels and time plots, plus a
local clock, on the SVG slots named in the configuration.

## Requirements

### Requirement: SVG background
The panel SHALL render `MAXI_synoptic_v2.svg` as its background, scaled to fill the window while keeping the SVG's aspect ratio, and centered. Space left over on two sides is filled with the SVG's background color.

#### Scenario: Window with a different aspect ratio
- **WHEN** the 1920x1080 SVG is shown in a 1000x1000 window
- **THEN** it is drawn 1000x562.5, centered vertically, and not distorted

### Requirement: Value overlays
For each `values` entry, the panel SHALL show a read-only value label exactly over the on-screen bounds of the SVG element with that id, connected to the entry's source. The label shows the Tango unit and the PyDM alarm border for the attribute quality.

#### Scenario: Label placement
- **WHEN** `MAXI_VAC_pressure_value` is configured and the window shows the SVG at scale 1
- **THEN** a label covers exactly the rectangle of that SVG element (its x, y, width and height, without its stroke), and shows the pressure with its unit

#### Scenario: Disconnected value
- **WHEN** the source of a value label is disconnected
- **THEN** the label shows PyDM's disconnected style

### Requirement: Plot overlays
For each `plots` entry, the panel SHALL show a time plot of the entry's source exactly over the on-screen bounds of the SVG element with that id. The plot adds the latest value every `refresh_period` seconds, even when the value has not changed, and starts empty.

#### Scenario: Slowly changing value
- **WHEN** a plotted pressure does not change for 60 s and `refresh_period` is 1.0
- **THEN** the plot shows a flat line with about 60 new points over that time

### Requirement: Plot colors follow the slot
A time plot SHALL use the fill color of its SVG slot as its background, and light axes and curve on a dark slot or dark ones on a light slot.

#### Scenario: Dark slot
- **WHEN** a plot slot has the fill `#15181c`
- **THEN** the plot has that background and light axes

### Requirement: Overlays follow transforms and resizing
Overlay bounds SHALL be the element's bounds after all SVG transforms of the element and its ancestors. When the window is resized, overlays move and resize with the SVG. Font sizes do not scale: the panel is intended for a fixed window size of 1920x1080.

#### Scenario: Transformed slot
- **WHEN** a value slot is inside a group with `transform="translate(0,-729)"`
- **THEN** the label is placed at the element's translated position, not at its raw coordinates

#### Scenario: Window resize
- **WHEN** the window is resized from 1920x1080 to 960x540
- **THEN** every overlay keeps its position relative to the SVG, at half its size, and the font size of the values stays the same

### Requirement: Value style sheet
The font size and text color of the value labels and of the clock SHALL come from the Qt style sheet `maxi_synoptic.qss` next to the display file, not from the desktop theme and not from the code.

#### Scenario: Font size from the style sheet
- **WHEN** `maxi_synoptic.qss` sets `font-size: 20px` for `PyDMLabel`
- **THEN** every value label shows its text 20 px high

#### Scenario: Dark desktop theme
- **WHEN** the desktop theme has light text and `maxi_synoptic.qss` sets a dark `color` for `PyDMLabel`
- **THEN** the values are shown in the dark color of the style sheet

### Requirement: Local clock
The panel SHALL show the local date and time in `DATETIME_value`, updated every second. This slot is not configured in the YAML.

#### Scenario: Clock display
- **WHEN** the panel is running
- **THEN** `DATETIME_value` shows the current local date and time, and it changes once per second

### Requirement: Read-only panel
No widget on the panel SHALL write to the control system.

#### Scenario: Clicking a value
- **WHEN** an operator clicks or types on a value label or plot
- **THEN** no value is written to any Tango attribute
