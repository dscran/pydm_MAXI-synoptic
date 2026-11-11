# Spec Delta

## MODIFIED Requirements

### Requirement: Runs without a Tango database
The simulator SHALL run without a Tango database, from the command line on a fixed port (default 45678, set with `--port`), and inside tests through a Tango test context. Clients address it as `tango://<host>:<port>/maxi/sim/1/<attribute>#dbase=no`. On the command line it is started with the installed command `maxi-synoptic-sim`.

#### Scenario: Manual start
- **WHEN** a user runs `maxi-synoptic-sim --port 45678`
- **THEN** `tango://localhost:45678/maxi/sim/1/<attribute>#dbase=no` can be read until the simulator is stopped

### Requirement: Simulator configuration
The installed package SHALL contain `maxi_synoptic_sim.yaml`, the bundled configuration named `sim`, which connects every value slot, plot and rule channel of the panel to the simulator on its default port. It passes startup validation against the bundled SVG with no errors and no warnings.

#### Scenario: Panel on the simulator
- **WHEN** the simulator runs with default settings and the panel is started with `maxi-synoptic --config sim`
- **THEN** the panel starts without validation errors or warnings, and every value slot shows a value
