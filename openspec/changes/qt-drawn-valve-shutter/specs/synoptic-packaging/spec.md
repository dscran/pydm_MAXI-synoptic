# Spec Delta

## MODIFIED Requirements

### Requirement: Bundled resources
The installed package SHALL contain the panel's Designer file, the Designer files of the valve and the shutter, the style sheet, the images of the drawing, and the configurations `default.json` and `sim.json`, and the panel SHALL load them from the installed package, independent of the current directory.

#### Scenario: Start outside the checkout
- **WHEN** the panel is started from a directory that contains no project files
- **THEN** it shows the bundled drawing with the bundled style sheet

#### Scenario: Images found next to the Designer file
- **WHEN** the package is installed into a different environment
- **THEN** the panel shows the drawing, the valve and the shutter, without settings for their location
