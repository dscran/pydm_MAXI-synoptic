"""Checks of a configuration and the rules against the ids of the SVG. This module does not import Qt."""

from __future__ import annotations

from typing import Iterable, Protocol

from synoptic.config import Config

SLOT_SUFFIXES = ("_value", "_plot")
CLOCK_ID = "DATETIME_value"


class Rule(Protocol):
    """What the validation needs to know about a color or state rule."""

    channel: str

    @property
    def element_ids(self) -> frozenset[str]: ...


def validate(config: Config, svg_ids: set[str], rules: Iterable[Rule]) -> tuple[list[str], list[str]]:
    """Return the errors and the warnings found. Errors mean that the panel must not start."""
    rules = list(rules)
    errors = [
        *_missing_slots(config, svg_ids),
        *_duplicate_slots(config),
        *_missing_rule_elements(rules, svg_ids),
        *_missing_rule_channels(rules, config),
    ]
    warnings = [*_unconfigured_slots(config, svg_ids), *_unused_channels(rules, config)]
    return errors, warnings


def _no_element(element_id):
    return f"no SVG element with id '{element_id}'"


def _missing_slots(config, svg_ids):
    sections = (("values", config.values), ("plots", config.plots))
    return [
        f"{section_name}.{element_id}: {_no_element(element_id)}"
        for section_name, entries in sections
        for element_id in entries
        if element_id not in svg_ids
    ]


def _duplicate_slots(config):
    return [
        f"'{element_id}' is in both values and plots"
        for element_id in config.values
        if element_id in config.plots
    ]


def _missing_rule_elements(rules, svg_ids):
    return [
        f"rule for channel '{rule.channel}': {_no_element(element_id)}"
        for rule in rules
        for element_id in sorted(rule.element_ids)
        if element_id not in svg_ids
    ]


def _missing_rule_channels(rules, config):
    return [
        f"rule channel '{rule.channel}' is not in extra_channels"
        for rule in rules
        if rule.channel not in config.extra_channels
    ]


def _unconfigured_slots(config, svg_ids):
    configured = {CLOCK_ID, *config.values, *config.plots}
    return [
        f"SVG element '{element_id}' is not configured"
        for element_id in sorted(svg_ids)
        if element_id.endswith(SLOT_SUFFIXES) and element_id not in configured
    ]


def _unused_channels(rules, config):
    used = {rule.channel for rule in rules}
    return [
        f"extra channel '{name}' is not used by any rule"
        for name in config.extra_channels
        if name not in used
    ]
