"""Console commands `maxi-synoptic` (the panel) and `maxi-synoptic-sim` (the simulator)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import re
import sys
from pathlib import Path

from pydm_launcher.main import main as pydm_main

from maxi_synoptic.sim import main as sim_main

__all__ = ["main", "sim_main"]

logger = logging.getLogger(__name__)

RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
UI_FILE = RESOURCES_DIR / "maxi_synoptic.ui"
STYLE_SHEET = RESOURCES_DIR / "maxi_synoptic.qss"
CONFIG_SUFFIX = ".json"
DEFAULT_CONFIG = "default"
BUNDLED_CONFIGS = {name: RESOURCES_DIR / f"{name}{CONFIG_SUFFIX}" for name in ("default", "sim")}

# A calc:// channel is a URL, which ends at the first `#`. The signals used inside the calc channel of
# the .ui therefore get a second macro, `<signal>_calc`, with `#` encoded.
CALC_SUFFIX = "_calc"
MACRO_PATTERN = re.compile(r"\$\{(\w+)\}")

TANGO_PLUGIN_MODULE = "pydm.data_plugins.tango_plugin"
MISSING_TANGO_PLUGIN = (
    "the installed PyDM has no Tango data plugin; install PyDM from github.com/dschick/pydm, "
    "branch tango_plugin (see the README of maxi-synoptic)"
)


class ConfigError(Exception):
    """The configuration cannot be used. Holds every error found, not only the first."""

    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


def main() -> None:
    """Start PyDM with the MAXI synoptic. `--config` selects the configuration, the rest goes to PyDM."""
    try:
        sys.argv = pydm_argv(sys.argv[1:])
    except ConfigError as error:
        sys.exit("maxi-synoptic: " + "\nmaxi-synoptic: ".join(error.errors))
    pydm_main()


def pydm_argv(args: list[str]) -> list[str]:
    """Build PyDM's command line from the arguments of `maxi-synoptic`."""
    # No own help and no abbreviations, so that `--help` and every PyDM option reach PyDM unchanged
    parser = argparse.ArgumentParser(prog="maxi-synoptic", add_help=False, allow_abbrev=False)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("-m", "--macro")
    own_args, pydm_args = parser.parse_known_args(args)
    if own_args.macro is not None:
        parser.error("-m/--macro is not supported; use --config to choose the configuration")

    signals = load_config(config_path(own_args.config))
    check_tango_plugin()
    macros = json.dumps(panel_macros(signals))
    return ["pydm", *pydm_args, "-m", macros, "--stylesheet", str(STYLE_SHEET), str(UI_FILE)]


def config_path(value: str) -> Path:
    """The configuration file named by `--config`: a bundled name, or a path from the current directory."""
    if "/" in value or value.endswith(CONFIG_SUFFIX):
        return Path(value).expanduser().resolve()
    if value not in BUNDLED_CONFIGS:
        known_names = ", ".join(sorted(BUNDLED_CONFIGS))
        raise ConfigError([f"'{value}' is not a bundled configuration; known names: {known_names}"])
    return BUNDLED_CONFIGS[value]


def load_config(path: Path) -> dict[str, str]:
    """Read a configuration file and check it against the signals of the panel."""
    try:
        text = path.read_text()
    except OSError as error:
        raise ConfigError([f"cannot read configuration {path}: {error.strerror}"]) from error
    try:
        signals = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError([f"{path}, line {error.lineno}: invalid JSON: {error.msg}"]) from error
    errors = config_errors(signals, panel_signals())
    if errors:
        raise ConfigError([f"{path}: {message}" for message in errors])
    for name in sorted(set(signals) - panel_signals()):
        logger.warning("%s: signal '%s' is not used by the panel", path, name)
    return signals


def config_errors(signals: object, needed: set[str]) -> list[str]:
    """Every reason why `signals` is not a mapping of each needed signal to an address."""
    if not isinstance(signals, dict):
        return ["the configuration must be a JSON object of signal names and addresses"]
    errors = [f"signal '{name}' is missing" for name in sorted(needed - set(signals))]
    for name, address in signals.items():
        if not isinstance(address, str):
            errors.append(f"signal '{name}' must be an address in quotes, not {json.dumps(address)}")
    return errors


def panel_signals() -> set[str]:
    """The signals that the panel's Designer file uses, without those that the command adds."""
    used = set(MACRO_PATTERN.findall(UI_FILE.read_text()))
    return {name for name in used if not name.endswith(CALC_SUFFIX)}


def panel_macros(signals: dict[str, str]) -> dict[str, str]:
    """The PyDM macros of the panel: the signals, plus `<signal>_calc` for use inside calc channels."""
    calc_macros = {name + CALC_SUFFIX: address.replace("#", "%23") for name, address in signals.items()}
    return {**signals, **calc_macros}


def check_tango_plugin() -> None:
    # find_spec does not import the plugin, which reads its poll period only when PyDM loads it
    if importlib.util.find_spec(TANGO_PLUGIN_MODULE) is None:
        raise ConfigError([MISSING_TANGO_PLUGIN])
