# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- The code is in loose top-level modules: `maxi_synoptic.py` (the PyDM `Display`), `maxi_rules.py`
  (registers rules when imported), the core package `synoptic/`, and `sim/maxi_sim.py`.
- `maxi_synoptic.py` finds the SVG and the QSS through `Path(__file__).parent`, and
  `synoptic.config.config_path(display_file, macros)` resolves the `config` macro against the same
  directory.
- `tests/conftest.py` puts the repository on `sys.path`; `test_rules.py` and `test_maxi_synoptic.py`
  read `MAXI_synoptic_v2.svg` and the YAML files from the repository root.
- PyDM loads a `.py` display by file path (not by module name), so the display file cannot use relative
  imports.
- The Tango plugin reads `PYDM_TANGO_POLL_PERIOD` only when it is loaded. `apply_poll_period` must run
  before the plugin is imported, so the plugin check must not import it.
- `pyproject.toml` has only pytest and ruff settings; there is no build configuration yet.

## Goals / Non-Goals

**Goals:**
- One `pip install` gives the commands `maxi-synoptic` and `maxi-synoptic-sim`, which work from any
  directory.
- Tests run against the installed (editable) package, so a missing package data file fails a test.
- Keep the git history of the moved files (`git mv`).

**Non-Goals:**
- No behavior change of display, overlays, rules, validation or simulator beyond the config location.
- No version automation (e.g. `setuptools-scm`); the version is written by hand.

## Decisions

### D1: `src/` layout, one package `maxi_synoptic`

```
src/maxi_synoptic/
  __init__.py
  display.py          # was maxi_synoptic.py   (class MaxiSynoptic)
  maxi_rules.py       # was maxi_rules.py
  sim.py              # was sim/maxi_sim.py
  cli.py              # new: maxi-synoptic and maxi-synoptic-sim
  resources/
    MAXI_synoptic_v2.svg
    maxi_synoptic.qss
    maxi_synoptic.yaml
    maxi_synoptic_sim.yaml
  synoptic/           # was synoptic/ (generic core, unchanged apart from imports and config_path)
```

The `src/` layout keeps the checkout itself off the import path, so tests only pass if the installed
package is complete. The MAXI rules keep the name `maxi_rules` (not `rules`), so they are not confused
with the core module `maxi_synoptic.synoptic.rules`.

*Alternative:* a flat layout with the package at the root. Rejected: `pytest` from the root would import
the checkout and hide missing package data.

### D2: setuptools with static metadata

`[build-system] requires = ["setuptools>=64"]` (64 is the first version with PEP 660 editable
installs), `[project]` with name, version `0.1.0`, `requires-python = ">=3.10"`, dependencies,
`[project.optional-dependencies] test`, `[project.scripts]`, and
`[tool.setuptools.package-data] maxi_synoptic = ["resources/*"]`. The existing pytest and ruff sections
stay.

*Alternative:* hatchling. Rejected only to match PyDM, which also uses setuptools; either would work.

### D3: Resources through `Path(__file__)`

`display.py` defines `RESOURCES = Path(__file__).resolve().parent / "resources"`. pip always unpacks
wheels, so the files exist on disk, and Qt (`QSvgRenderer`, `setStyleSheet(path)`) needs real paths
anyway.

*Alternative:* `importlib.resources.files()` + `as_file()`. More general (zip imports), but adds context
managers around Qt calls for a case that does not occur here.

### D4: Absolute imports everywhere

All modules import `maxi_synoptic.…` absolutely. `display.py` must do so because PyDM loads it by path
under a different module name; the other modules do so for consistency. Importing
`maxi_synoptic.maxi_rules` from the display file uses the normal `sys.modules` entry, so the rules are
registered once, even if PyDM executes the display file as a second module.

### D5: Config resolution in the core, bundled names from the display

`config_path(display_file, macros)` becomes
`config_path(macros, bundled: Mapping[str, Path], default: str = "default") -> Path`. It raises
`ConfigError` for an unknown bundled name, listing the known names. Rule from the spec: a value without
`/` and without a `.yaml`/`.yml` suffix is a bundled name; anything else is a path, resolved with
`Path(value).expanduser().resolve()` against the current directory. The display passes
`{"default": RESOURCES / "maxi_synoptic.yaml", "sim": RESOURCES / "maxi_synoptic_sim.yaml"}`. The core
stays free of MAXI names. The `ConfigError` goes through the existing `_stop_on_errors` path, so it is
logged like other configuration errors.

### D6: `maxi-synoptic` command wraps the PyDM launcher

`cli.main()` parses `--config` with `argparse.parse_known_args`, resolves a path value to an absolute
path (so it does not depend on what PyDM does with the current directory), and calls
`pydm_launcher.main.main()` with
`sys.argv = ["pydm", *unknown_args, "-m", json.dumps({"config": value}), str(display_file)]`.
The macro is passed as JSON because PyDM's `KEY=value` macro syntax splits at commas, which can occur
in paths. If the user also passes `-m`/`--macro`, the command stops with an error rather than merging
macro sets (the panel has no other macros).

*Alternative:* start `pydm` as a subprocess. Rejected: an extra process, and the `pydm` script might be
a different installation than the imported `pydm`.

`cli.sim_main()` is `maxi_synoptic.sim.main` re-exported; the sim module keeps its own `main()` so
`python -m maxi_synoptic.sim` also works.

### D7: Tango plugin check without importing the plugin

At the start of `MaxiSynoptic.__init__`, before `apply_poll_period`, the display checks
`importlib.util.find_spec("pydm.data_plugins.tango_plugin")`. If it is `None`, it raises `ConfigError`
with one message: the Tango plugin is missing, install PyDM from `dschick/pydm` branch `tango_plugin`
(see README). `find_spec` on a submodule imports only the parent packages (`pydm.data_plugins`), which
are already imported by `pydm`, so the plugin itself is not loaded and the poll period still applies.

*Alternative:* check `data_plugins.plugin_for_address("tango://…")`. Rejected: it loads the plugin
before the poll period is set (see Context).

### D8: Tests use the installed package

`conftest.py` keeps `QT_QPA_PLATFORM=offscreen` and drops the `sys.path` insert. Tests read bundled files
through `maxi_synoptic.display.RESOURCES`. `test_config.py`'s `config_path` tests are rewritten for D5
(default, bundled name, unknown name, relative path with `monkeypatch.chdir`, absolute path,
`.yml` suffix). New `tests/test_cli.py` checks the argv built by `cli.main` (with the PyDM launcher
patched out) and the `-m` conflict. A packaging test builds a wheel and checks it contains the four
resource files and only the top-level package `maxi_synoptic`.

## Risks / Trade-offs

- [Users install upstream `pydm` from PyPI and get no Tango plugin] → D7 stops the panel with a message
  that names the fix; the README puts the fork installation first.
- [`pip install` pulls PyPI `pydm`'s dependencies (`pyepics`, …) into a conda environment] → README
  recommends installing the conda packages first; pip then finds them satisfied.
- [`pip install` of upstream `pydm` replaces an editable install of the fork] → README installs the fork
  first; pip keeps an already satisfied `pydm`.
- [The user loses "relative to the display" config paths] → BREAKING note in the README; relative to the
  current directory is what users expect from a command.
- [Editing the SVG in Inkscape now means editing `src/maxi_synoptic/resources/MAXI_synoptic_v2.svg`] →
  README "Editing the SVG" names the new path; with an editable install, the change shows on the next
  start.

## Migration Plan

1. In the existing environment: `pip install -e ../pydm --no-deps` (instead of `PYTHONPATH=../pydm`),
   then `pip install -e .[test]`.
2. Replace `python -m pydm_launcher.main [-m config=X] maxi_synoptic.py` with
   `maxi-synoptic [--config X]`, and `python sim/maxi_sim.py` with `maxi-synoptic-sim`.
3. Rollback: `pip uninstall maxi-synoptic` and check out the previous commit.
