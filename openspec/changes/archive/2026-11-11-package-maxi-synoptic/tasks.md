# Tasks

Before starting: the uncommitted work of `add-svg-synoptic-panel` is committed, and that change is
archived (`/opsx:archive`), so the `synoptic-config` and `maxi-simulator` deltas of this change apply to
`openspec/specs/`.

## 1. Package layout and build configuration

- [x] 1.1 Move the code with `git mv` into the layout of design D1: `synoptic/` → `src/maxi_synoptic/synoptic/`, `maxi_synoptic.py` → `src/maxi_synoptic/display.py`, `maxi_rules.py` → `src/maxi_synoptic/maxi_rules.py`, `sim/maxi_sim.py` → `src/maxi_synoptic/sim.py`, the SVG, QSS and both YAML files → `src/maxi_synoptic/resources/`; add `src/maxi_synoptic/__init__.py`; delete the empty `sim/`. Verify with `git status` that every file shows as renamed, and that `MAXI.svg` and `MAXI_synoptic.svg` are still at the root
- [x] 1.2 Change every import in `src/` and `tests/` to absolute `maxi_synoptic.…` imports (D4), and in `display.py` define `RESOURCES` and load the SVG and QSS from it (D3). Verify with `grep -rnE "^(from|import) (synoptic|maxi_rules|sim)\b|^import maxi_synoptic$" src tests` returning nothing, and `ruff check src tests`
- [x] 1.3 Add `[build-system]` and `[project]` to `pyproject.toml` as in D2 (dependencies, `test` extra, `requires-python`, package data; scripts follow in group 3), keeping the pytest and ruff sections. Verify that `pip install -e .[test]` succeeds in the `maxi-synoptic` environment
- [x] 1.4 Remove the `sys.path` insert from `tests/conftest.py`, and make `test_rules.py` and `test_maxi_synoptic.py` read the SVG and YAML through `maxi_synoptic.display.RESOURCES` (D8). Verify that `pytest tests` passes from the repository root and that `python -c "import maxi_synoptic"` works from `/tmp`

## 2. Configuration location

- [x] 2.1 Rewrite `config_path` in `maxi_synoptic/synoptic/config.py` as in D5 (bundled names, paths relative to the current directory, `ConfigError` for unknown names), and pass the two bundled configurations from `display.py`. Verify with the rewritten `config_path` tests in `tests/test_config.py`: default, `sim`, unknown name lists `default` and `sim`, relative path with `monkeypatch.chdir`, absolute path, `.yml` suffix
- [x] 2.2 Add a test to `tests/test_maxi_synoptic.py` that an unknown bundled name stops the panel with a `ConfigError`, and update the comments in both YAML files that mention `maxi_synoptic.py` or "next to the display". Verify with `pytest tests/test_maxi_synoptic.py` and `grep -n "maxi_synoptic.py\|next to" src/maxi_synoptic/resources/*.yaml` returning nothing

## 3. Commands

- [x] 3.1 Add `cli.py` with `main()` for `maxi-synoptic` (D6: `--config`, absolute path for path values, JSON macro, other arguments passed through, error on `-m`/`--macro`) and `sim_main()`; add both to `[project.scripts]`. Verify with new `tests/test_cli.py` (launcher patched out): argv for no option, `--config sim`, `--config ./x.yaml` → absolute path, a path with a comma, passthrough of `--hide-nav-bar`, and the `-m` error
- [x] 3.2 Reinstall with `pip install -e .[test]` and check the commands by hand: `maxi-synoptic-sim --drift` in one terminal and `maxi-synoptic --config sim` in a second one (or with `QT_QPA_PLATFORM=offscreen` and a screenshot), both started from a directory outside the checkout. Verify that the panel starts without validation warnings and shows drifting values, and that `maxi-synoptic --help` shows PyDM's help

## 4. Tango plugin check

- [x] 4.1 Add the check of design D7 at the start of `MaxiSynoptic.__init__`, before `apply_poll_period`. Verify with a test in `tests/test_maxi_synoptic.py` that patches `importlib.util.find_spec` to return `None` for the plugin and expects a `ConfigError` naming the Tango plugin, and with the existing poll period tests still passing (the check does not load the plugin)

## 5. Packaging check and documentation

- [x] 5.1 Add `tests/test_packaging.py`, which builds a wheel into `tmp_path` (`pip wheel . --no-deps --no-build-isolation`) and checks that it contains the four resource files and no top-level entry other than `maxi_synoptic` and its `.dist-info`. Verify with `pytest tests/test_packaging.py`
- [x] 5.2 Rewrite the README: installation (conda packages first, then the PyDM fork with the Tango plugin via `pip install -e ../pydm --no-deps` or the git URL, then `pip install .`; PyQt5 from conda), running with `maxi-synoptic [--config sim|<path>]`, the simulator with `maxi-synoptic-sim`, the new config resolution as a BREAKING note, the SVG path under `src/maxi_synoptic/resources/`, and the new code layout table. Verify that each command in the README runs as written in a fresh environment created as the README describes

## 6. Integration

- [x] 6.1 In a fresh conda environment created from the README, run `pip install .` (not editable) and `pytest tests` from the repository root, then start the panel on the simulator from `/tmp`. Verify that all tests pass and the panel runs with the installed (non-editable) package
- [x] 6.2 Run `openspec validate package-maxi-synoptic --strict` and verify that it passes

## Workflow follow-up

- Archive this change after review (`/opsx:archive`), which updates `synoptic-config` and
  `maxi-simulator` and creates `synoptic-packaging` in `openspec/specs/`.
