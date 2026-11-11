"""YAML configuration of a synoptic panel: loading, schema checks and Tango addresses.

This module does not import Qt, so it can be tested on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

import yaml

DEFAULT_CONFIG_NAME = "maxi_synoptic.yaml"
CONFIG_MACRO = "config"
DEFAULT_TIME_SPAN = 600.0
DEFAULT_FLOAT_PRECISION = 6
TANGO_PROTOCOL = "tango://"

SECTIONS = ("defaults", "values", "plots", "extra_channels")
DEFAULTS_KEYS = {"tango_host", "tango_poll_period", "max_redraw_rate"}
VALUE_KEYS = {"source", "format"}
PLOT_KEYS = {"source", "refresh_period", "log_y", "time_span", "y_range"}

EXPONENTIAL = "exponential"
DECIMAL = "decimal"
STRING = "string"

PRINTF_PATTERN = re.compile(r"%[-+ #0]*\d*(?:\.(\d+))?([diouxXeEfFgGs])")
QUOTING_HINT = "values starting with '%' must be quoted, e.g. format: \"%6.3f\""


class ConfigError(Exception):
    """The configuration cannot be used. `errors` lists every problem that was found."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("Invalid synoptic configuration:\n" + "\n".join(f"  - {error}" for error in errors))


@dataclass(frozen=True)
class ValueFormat:
    """How a value label formats numbers: one of EXPONENTIAL, DECIMAL or STRING, plus the precision."""

    display_format: str
    precision: int | None = None


@dataclass(frozen=True)
class ValueEntry:
    source: str | None
    format: ValueFormat | None = None


@dataclass(frozen=True)
class PlotEntry:
    source: str | None
    refresh_period: float | None
    log_y: bool = False
    time_span: float = DEFAULT_TIME_SPAN
    # (lowest, highest) value of a fixed y-axis. None lets the axis follow the data.
    y_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class Defaults:
    tango_host: str | None = None
    tango_poll_period: float | None = None
    max_redraw_rate: int | None = None


@dataclass(frozen=True)
class Config:
    """The parsed configuration.

    An entry with a schema error is still listed, with `None` for the broken key, so that its id can be
    checked against the SVG. Such a config always comes with errors and must not be used to build a panel.
    """

    defaults: Defaults = field(default_factory=Defaults)
    values: dict[str, ValueEntry] = field(default_factory=dict)
    plots: dict[str, PlotEntry] = field(default_factory=dict)
    extra_channels: dict[str, str] = field(default_factory=dict)

    def address(self, source: str) -> str:
        """Return the PyDM channel address for a `source` or extra channel of this configuration."""
        return resolve_address(source, self.defaults.tango_host)


def resolve_address(source: str, tango_host: str | None = None) -> str:
    """Turn a Tango attribute name into a PyDM address. A full `tango://` address is kept as it is."""
    if source.startswith(TANGO_PROTOCOL):
        return source
    if tango_host:
        return f"{TANGO_PROTOCOL}{tango_host}/{source}"
    return TANGO_PROTOCOL + source


def parse_format(text: str) -> ValueFormat:
    """Parse a printf format like `%.2e`. Width and flags are accepted but have no effect.

    Raises ValueError if `text` is not a single printf conversion.
    """
    match = PRINTF_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"invalid format {text!r} (expected a printf format like '%.2e')")
    precision_text, conversion = match.groups()
    if conversion == "s":
        return ValueFormat(STRING)
    if conversion in "diouxX":
        return ValueFormat(DECIMAL, 0)
    precision = DEFAULT_FLOAT_PRECISION if precision_text is None else int(precision_text)
    if conversion in "eE":
        return ValueFormat(EXPONENTIAL, precision)
    return ValueFormat(DECIMAL, precision)


def config_path(display_file: str | Path, macros: Mapping[str, str] | None = None) -> Path:
    """Return the configuration file of a display: the `config` macro, or the default name next to it."""
    display_dir = Path(display_file).resolve().parent
    file_name = (macros or {}).get(CONFIG_MACRO) or DEFAULT_CONFIG_NAME
    return display_dir / file_name


def load_config(path: str | Path) -> tuple[Config, list[str]]:
    """Read a configuration file. Returns the configuration and all errors found in it."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return Config(), [f"cannot read configuration file {path}: {error.strerror}"]
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        return Config(), [f"{path}: {_describe_yaml_error(error)}"]
    return parse_config(data)


def parse_config(data: Any) -> tuple[Config, list[str]]:
    """Check loaded YAML data against the schema. Returns the configuration and all errors found."""
    if data is None:
        return Config(), []
    if not isinstance(data, dict):
        return Config(), ["the configuration must be a mapping with the sections " + ", ".join(SECTIONS)]
    errors = [f"unknown top-level key {key!r}" for key in data if key not in SECTIONS]
    config = Config(
        defaults=_parse_defaults(_section(data, "defaults", errors), errors),
        values=_parse_entries(_section(data, "values", errors), "values", _parse_value, errors),
        plots=_parse_entries(_section(data, "plots", errors), "plots", _parse_plot, errors),
        extra_channels=_parse_extra_channels(_section(data, "extra_channels", errors), errors),
    )
    return config, errors


def _describe_yaml_error(error):
    mark = getattr(error, "problem_mark", None)
    if mark is None:
        return f"YAML syntax error: {error}"
    problem = getattr(error, "problem", None) or "invalid syntax"
    message = f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}: {problem}"
    if "'%'" in problem:
        message += f" ({QUOTING_HINT})"
    return message


def _section(data, name, errors):
    section = data.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        errors.append(f"{name}: must be a mapping")
        return {}
    return section


def _unknown_keys(mapping, allowed, where):
    return [f"{where}: unknown key {key!r}" for key in mapping if key not in allowed]


def _parse_defaults(section, errors):
    errors.extend(_unknown_keys(section, DEFAULTS_KEYS, "defaults"))
    tango_host = section.get("tango_host")
    if tango_host is not None and not _is_text(tango_host):
        errors.append(f"defaults: 'tango_host' must be a string like 'host:10000', got {tango_host!r}")
        tango_host = None
    poll_period = _positive_number(section, "tango_poll_period", "defaults", errors)
    max_redraw_rate = _positive_integer(section, "max_redraw_rate", "defaults", errors)
    return Defaults(tango_host=tango_host, tango_poll_period=poll_period, max_redraw_rate=max_redraw_rate)


def _parse_entries(section, section_name, parse_entry, errors):
    entries = {}
    for element_id, entry in section.items():
        where = f"{section_name}.{element_id}"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a mapping with a 'source'")
            entry = {}
        entries[str(element_id)] = parse_entry(entry, where, errors)
    return entries


def _parse_value(entry, where, errors):
    errors.extend(_unknown_keys(entry, VALUE_KEYS, where))
    return ValueEntry(source=_source(entry, where, errors), format=_value_format(entry, where, errors))


def _parse_plot(entry, where, errors):
    errors.extend(_unknown_keys(entry, PLOT_KEYS, where))
    if "refresh_period" not in entry:
        errors.append(f"{where}: missing 'refresh_period'")
    time_span = DEFAULT_TIME_SPAN
    if "time_span" in entry:
        time_span = _positive_number(entry, "time_span", where, errors)
    log_y = _log_y(entry, where, errors)
    return PlotEntry(
        source=_source(entry, where, errors),
        refresh_period=_positive_number(entry, "refresh_period", where, errors),
        log_y=log_y,
        time_span=time_span,
        y_range=_y_range(entry, log_y, where, errors),
    )


def _parse_extra_channels(section, errors):
    channels = {}
    for name, address in section.items():
        if _is_text(address):
            channels[str(name)] = address
        else:
            errors.append(f"extra_channels.{name}: must be a Tango address string, got {address!r}")
    return channels


def _source(entry, where, errors):
    if "source" not in entry:
        errors.append(f"{where}: missing 'source'")
        return None
    source = entry["source"]
    if not _is_text(source):
        errors.append(f"{where}: 'source' must be a Tango address string, got {source!r}")
        return None
    return source


def _value_format(entry, where, errors):
    if "format" not in entry:
        return None
    try:
        return parse_format(str(entry["format"]))
    except ValueError as error:
        errors.append(f"{where}: {error}")
        return None


def _log_y(entry, where, errors):
    log_y = entry.get("log_y", False)
    if isinstance(log_y, bool):
        return log_y
    errors.append(f"{where}: 'log_y' must be true or false, got {log_y!r}")
    return False


def _y_range(entry, log_y, where, errors):
    """Return entry["y_range"] as (lowest, highest), or None if it is missing or invalid (which adds an error)."""
    if "y_range" not in entry:
        return None
    y_range = entry["y_range"]
    is_pair = isinstance(y_range, list) and len(y_range) == 2 and all(_is_number(limit) for limit in y_range)
    if not is_pair or y_range[0] >= y_range[1]:
        errors.append(f"{where}: 'y_range' must be [lowest, highest] with lowest < highest, got {y_range!r}")
        return None
    if log_y and y_range[0] <= 0:
        errors.append(f"{where}: 'y_range' must be above 0 with log_y, got {y_range!r}")
        return None
    lowest, highest = y_range
    return float(lowest), float(highest)


def _positive_number(mapping, key, where, errors):
    """Return mapping[key] as a float, or None if the key is missing or invalid (which adds an error)."""
    if key not in mapping:
        return None
    number = mapping[key]
    if _is_number(number) and number > 0:
        return float(number)
    errors.append(f"{where}: {key!r} must be a number > 0, got {number!r}")
    return None


def _positive_integer(mapping, key, where, errors):
    """Return mapping[key] as an int, or None if the key is missing or invalid (which adds an error)."""
    if key not in mapping:
        return None
    number = mapping[key]
    is_integer = isinstance(number, int) and not isinstance(number, bool)
    if is_integer and number > 0:
        return number
    errors.append(f"{where}: {key!r} must be a whole number > 0, got {number!r}")
    return None


def _is_number(value):
    return isinstance(value, Real) and not isinstance(value, bool)


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""
