# Spec Delta

## MODIFIED Requirements

### Requirement: Declared dependencies
The distribution SHALL declare `pydm` and `pytango` as runtime dependencies, and `pytest`, `pytest-qt` and `pytest-timeout` in an extra named `test`. It SHALL NOT declare a Qt binding or a direct URL dependency.

#### Scenario: Test extra
- **WHEN** a user runs `pip install -e .[test]`
- **THEN** the test dependencies are installed as well, and `pytest tests` runs against the installed package

#### Scenario: Existing PyQt5 is kept
- **WHEN** the package is installed into a conda environment that has PyQt5 from conda-forge
- **THEN** pip does not install or replace any Qt binding

#### Scenario: No YAML library needed
- **WHEN** the package is installed into an environment without PyYAML
- **THEN** the panel and the simulator start

### Requirement: Bundled resources
The installed package SHALL contain the panel's Designer file, the style sheet, the images of the drawing, and the configurations `default.json` and `sim.json`, and the panel SHALL load them from the installed package, independent of the current directory.

#### Scenario: Start outside the checkout
- **WHEN** the panel is started from a directory that contains no project files
- **THEN** it shows the bundled drawing with the bundled style sheet

#### Scenario: Images found next to the Designer file
- **WHEN** the package is installed into a different environment
- **THEN** the panel shows the drawing and every state drawing, without settings for their location

### Requirement: Panel command
Installing the distribution SHALL provide the command `maxi-synoptic`, which starts PyDM with the installed Designer file and style sheet. The option `--config <value>` selects the configuration; its signals are passed to PyDM as macros. All other arguments SHALL be passed to PyDM unchanged, except PyDM's own `-m`/`--macro`, which is refused.

#### Scenario: Default start
- **WHEN** a user runs `maxi-synoptic`
- **THEN** PyDM opens the MAXI synoptic with the bundled default configuration and the bundled style sheet

#### Scenario: Simulator configuration
- **WHEN** a user runs `maxi-synoptic --config sim`
- **THEN** the panel uses the bundled simulator configuration

#### Scenario: PyDM options pass through
- **WHEN** a user runs `maxi-synoptic --config sim --hide-nav-bar`
- **THEN** PyDM receives `--hide-nav-bar`

#### Scenario: Macro option refused
- **WHEN** a user runs `maxi-synoptic -m '{"maxi_vac_pressure": "..."}'`
- **THEN** the command stops with an error that says to use `--config`

### Requirement: Tango plugin check
When the installed PyDM has no Tango data plugin, the `maxi-synoptic` command SHALL NOT start PyDM, and it SHALL report an error that says the Tango plugin is missing and how to install a PyDM that has it.

#### Scenario: PyDM without Tango plugin
- **WHEN** `maxi-synoptic` is run in an environment with a PyDM release that has no Tango plugin
- **THEN** it stops with an error that names the missing Tango plugin and points to the installation instructions, and no PyDM window opens
