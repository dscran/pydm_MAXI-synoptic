# Spec Delta

## MODIFIED Requirements

### Requirement: Configuration file location
The panel SHALL read the bundled default configuration `maxi_synoptic.yaml` from the installed package, unless the PyDM macro `config` names another configuration. A macro value without a `/` and without a `.yaml` or `.yml` suffix is the name of a bundled configuration (`default` or `sim`). Any other value is a file path; a relative path is resolved against the current directory. An unknown bundled name is a configuration error that lists the known names.

#### Scenario: Default configuration file
- **WHEN** the panel is started without a `config` macro
- **THEN** it reads the bundled `maxi_synoptic.yaml`

#### Scenario: Bundled simulator configuration
- **WHEN** the panel is started with macro `config=sim`
- **THEN** it reads the bundled `maxi_synoptic_sim.yaml`

#### Scenario: Configuration file from macro
- **WHEN** the panel is started from directory `/home/op` with macro `config=other.yaml`
- **THEN** it reads `/home/op/other.yaml`

#### Scenario: Absolute path
- **WHEN** the panel is started with macro `config=/etc/maxi/panel.yaml`
- **THEN** it reads `/etc/maxi/panel.yaml`

#### Scenario: Unknown bundled name
- **WHEN** the panel is started with macro `config=simulator`
- **THEN** it does not start and reports that `simulator` is not a bundled configuration, naming `default` and `sim`
