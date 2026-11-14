# Spec Delta

## ADDED Requirements

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
