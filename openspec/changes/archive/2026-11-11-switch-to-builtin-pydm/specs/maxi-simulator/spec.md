# Spec Delta

## MODIFIED Requirements

### Requirement: Simulator configuration
The installed package SHALL contain `sim.json`, the bundled configuration named `sim`, which connects every signal of the panel to the simulator on its default port. It passes the configuration check of the `maxi-synoptic` command with no errors and no warnings.

#### Scenario: Panel on the simulator
- **WHEN** the simulator runs with default settings and the panel is started with `maxi-synoptic --config sim`
- **THEN** the panel starts without configuration errors or warnings, and every value slot shows a value
