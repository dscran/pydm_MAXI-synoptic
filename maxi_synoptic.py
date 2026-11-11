"""PyDM display of the MAXI synoptic: `pydm maxi_synoptic.py`, optionally with `-m config=<file>.yaml`."""

from __future__ import annotations

import functools
import logging
from pathlib import Path

from pydm import Display
from qtpy.QtWidgets import QVBoxLayout

import maxi_rules  # noqa: F401  (registers the MAXI rules)
from synoptic.config import Config, ConfigError, config_path, load_config
from synoptic.overlays import Overlays
from synoptic.poll_period import apply_poll_period
from synoptic.rules import RuleBinding, registered_rules
from synoptic.svg_view import SvgDom, SvgView
from synoptic.validation import CLOCK_ID, validate

logger = logging.getLogger(__name__)

DISPLAY_DIR = Path(__file__).resolve().parent
SVG_FILE = DISPLAY_DIR / "MAXI_synoptic_v2.svg"
STYLE_FILE = DISPLAY_DIR / "maxi_synoptic.qss"


class MaxiSynoptic(Display):
    """Shows MAXI_synoptic_v2.svg with live values, plots, colors and states from a YAML configuration."""

    def __init__(self, parent=None, args=None, macros=None):
        super().__init__(parent=parent, args=args, macros=macros)
        config, config_errors = load_config(config_path(__file__, macros))
        apply_poll_period(config.defaults.tango_poll_period)
        dom = SvgDom.from_file(SVG_FILE)
        rules = registered_rules()
        _stop_on_errors(config, config_errors, dom, rules)

        self.view = SvgView(dom, self)
        self.overlays = _build_overlays(self.view, config, dom)
        self.rule_bindings = _bind_rules(self.view, config, rules)
        # Show the unknown looks from the first frame on, not the looks the SVG was saved with
        self.view.flush()
        self.destroyed.connect(functools.partial(_disconnect_rules, self.rule_bindings))

        # Fonts and colors of the value labels and the clock
        self.setStyleSheet(str(STYLE_FILE))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def ui_filename(self):
        return None


def _stop_on_errors(config, config_errors, dom, rules):
    """Log every warning and error, and raise one ConfigError if there is any error."""
    validation_errors, warnings = validate(config, dom.ids(), rules)
    for warning in warnings:
        logger.warning(warning)
    errors = config_errors + validation_errors
    for error in errors:
        logger.error(error)
    if errors:
        raise ConfigError(errors)


def _build_overlays(view: SvgView, config: Config, dom: SvgDom) -> Overlays:
    overlays = Overlays(view)
    for element_id, entry in config.values.items():
        overlays.add_value(element_id, config.address(entry.source), entry.format)
    for element_id, entry in config.plots.items():
        overlays.add_plot(element_id, config.address(entry.source), entry, config.defaults.max_redraw_rate)
    if CLOCK_ID in dom.ids():
        overlays.add_clock(CLOCK_ID)
    return overlays


def _bind_rules(view: SvgView, config: Config, rules) -> list[RuleBinding]:
    bindings = [RuleBinding(rule, view, parent=view) for rule in rules]
    for binding in bindings:
        binding.connect(config.address(config.extra_channels[binding.rule.channel]))
    return bindings


def _disconnect_rules(bindings):
    for binding in bindings:
        binding.disconnect()
