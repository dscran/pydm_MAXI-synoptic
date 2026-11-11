# Proposal

## Why

The MAXI synoptic panel currently runs only from a checkout: the display, the rules and the core are
loose modules at the repository root, found through `PYTHONPATH` and `sys.path` tricks in the tests, and
the panel reads its SVG, style sheet and YAML from next to `maxi_synoptic.py`. To run it on a control
room machine, it must be installable with `pip install` into an environment that has PyDM and PyTango,
and startable with a single command.

## What Changes

- Add a `[project]` section to `pyproject.toml`: distribution `maxi-synoptic`, a build backend, the
  runtime dependencies (`pydm`, `pytango`, `pyyaml`, `numpy`, `qtpy`) and a `test` extra (`pytest`,
  `pytest-qt`, `pytest-timeout`).
- **BREAKING** Move all code into one import package `maxi_synoptic` (in a `src/` layout):
  - the generic core `synoptic/` becomes `maxi_synoptic.synoptic`
  - `maxi_synoptic.py` becomes `maxi_synoptic.display`, and `maxi_rules.py` becomes `maxi_synoptic.maxi_rules`
  - `sim/maxi_sim.py` becomes `maxi_synoptic.sim`
  - `MAXI_synoptic_v2.svg`, `maxi_synoptic.qss`, `maxi_synoptic.yaml` and `maxi_synoptic_sim.yaml`
    become package data
  The old top-level modules `synoptic`, `maxi_rules`, `maxi_synoptic` (as a file) and `sim` disappear.
- Add two console scripts:
  - `maxi-synoptic [--config X] [extra PyDM options]` starts PyDM with the installed display
  - `maxi-synoptic-sim [--port N] [--drift]` starts the simulator
- **BREAKING** Change how the `config` macro is resolved: without the macro the panel uses the bundled
  `maxi_synoptic.yaml`; `config=sim` selects the bundled simulator configuration; any other value is a
  file path, absolute or relative to the current directory (no longer relative to the display file).
- At startup, stop with a clear error if the installed PyDM has no Tango data plugin.
- Tests import the installed package (`pip install -e .[test]`) instead of putting the repository on
  `sys.path`.
- The README describes installation (including the PyDM fork with the Tango plugin), the two commands
  and how to edit the SVG in a checkout.

## Assumptions (please confirm)

1. **Python 3.10 or newer** (`requires-python = ">=3.10"`); the code already uses `X | Y` type syntax.
2. **setuptools** as build backend (as PyDM uses), with a static version `0.1.0`.
3. **PyQt5 is not a declared dependency**, like in PyDM itself: in conda environments it comes from
   conda-forge, and a pip `PyQt5` next to it breaks the environment. The README names it as a
   requirement.
4. **`pydm` is required by name only**; the Tango plugin from `dschick/pydm@tango_plugin` is installed
   by the user as documented. No version pin, because the fork has no own version tag.
5. **Only `MAXI_synoptic_v2.svg` is packaged.** `MAXI.svg` and `MAXI_synoptic.svg` stay in the
   repository for reference and are not installed.
6. **The tests stay outside the package** (`tests/` at the repository root) and are not installed.
7. Bundled configuration names are `default` (= `maxi_synoptic.yaml`) and `sim`
   (= `maxi_synoptic_sim.yaml`). A `config` value without a `/` and without a `.yaml`/`.yml` suffix is
   a bundled name; anything else is a path.

## Out of scope

- Publishing to PyPI or a package index, and building a conda recipe.
- Splitting the generic core into its own reusable distribution.
- Upstreaming the Tango plugin to PyDM or pinning a PyDM version.
- Any change to the panel's look, rules, overlays, validation or the simulator's behavior.
- Windows and macOS support beyond what PyDM and PyTango provide anyway.
- Real device names in `maxi_synoptic.yaml` (they stay placeholders).

## Capabilities

### New Capabilities
- `synoptic-packaging`: how the panel is installed and started: distribution metadata, dependencies,
  bundled resources, the `maxi-synoptic` and `maxi-synoptic-sim` commands, and the check for the Tango
  plugin.

### Modified Capabilities
- `synoptic-config`: the requirement "Configuration file location" changes: bundled default, bundled
  names, and paths relative to the current directory.
- `maxi-simulator`: the requirement "Runs without a Tango database" changes: the simulator is started
  with the `maxi-synoptic-sim` command instead of `python sim/maxi_sim.py`. The requirement "Simulator
  configuration" changes: the simulator YAML is bundled in the package and selected with `--config sim`.

Both capabilities are defined by the change `add-svg-synoptic-panel`, which is complete but not yet
archived. It must be archived first, so that these deltas apply to `openspec/specs/`.

## Impact

- Code: every module moves; all imports change from `synoptic.*`, `maxi_rules`, `maxi_synoptic`, `sim.*`
  to `maxi_synoptic.*`. `synoptic/config.py` (`config_path`) changes behavior.
- Tests: `tests/conftest.py` no longer edits `sys.path`; tests that read files from the repository root
  (`MAXI_synoptic_v2.svg`, YAML) read them from the installed package instead.
- Users: `python -m pydm_launcher.main maxi_synoptic.py` is replaced by `maxi-synoptic`;
  `python sim/maxi_sim.py` by `maxi-synoptic-sim`; `-m config=maxi_synoptic_sim.yaml` by
  `--config sim`.
- Dependencies: declared in `pyproject.toml` for the first time.
