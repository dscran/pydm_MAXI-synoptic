import math
from pathlib import Path

import numpy as np
import pytest

import maxi_rules
from maxi_rules import BLUE, GRAY, GREEN, YELLOW
from synoptic import rules
from synoptic.rules import UNKNOWN_COLOR, ColorRule, RuleBinding, StateRule, bands
from synoptic.svg_view import SvgDom, SvgView

MAXI_SVG = Path(__file__).parent.parent / "MAXI_synoptic_v2.svg"
ALARM_SEVERITY = 2
INVALID_SEVERITY = 3
RED = "#cc0000"


class FakeView:
    """Records what the rules show, like the SVG view would."""

    def __init__(self):
        self.fills = {}
        self.hatched = set()
        self.visible = {}

    def set_fill(self, element_id, color):
        self.fills[element_id] = color

    def set_hatched(self, element_id, is_hatched):
        if is_hatched:
            self.hatched.add(element_id)
        else:
            self.hatched.discard(element_id)

    def set_visible(self, element_id, is_visible):
        self.visible[element_id] = is_visible

    def shown(self):
        return {element_id for element_id, is_visible in self.visible.items() if is_visible}


@pytest.fixture
def view():
    return FakeView()


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setattr(rules, "REGISTRY", [])
    return rules.REGISTRY


def maxi_rule(channel):
    return next(rule for rule in rules.registered_rules() if rule.channel == channel)


def bind(channel, view, value=None):
    """Bind a MAXI rule to the view, connected and optionally with a first value."""
    binding = RuleBinding(maxi_rule(channel), view)
    binding.connection_changed(True)
    binding.severity_changed(0)
    if value is not None:
        binding.value_changed(value)
    return binding


def color_binding(view):
    rule = ColorRule("level", "TANK", lambda level: bands(level, [(10, GREEN)], above=RED))
    binding = RuleBinding(rule, view)
    binding.connection_changed(True)
    return binding


def state_binding(view, callback=lambda is_on: "ON" if is_on else "OFF"):
    rule = StateRule("switch", frozenset({"ON", "OFF"}), "UNSURE", callback)
    binding = RuleBinding(rule, view)
    binding.connection_changed(True)
    return binding


def assert_unknown_color(view, target="TANK"):
    assert view.fills[target] == UNKNOWN_COLOR
    assert target in view.hatched


def assert_known_color(view, color, target="TANK"):
    assert view.fills[target] == color
    assert target not in view.hatched


# --- framework ---


def test_decorators_register_rules(registry):
    @rules.color_rule(channel="level", target="TANK")
    def tank(level):
        return GREEN

    @rules.state_rule(channel="switch", assets={"ON", "OFF"}, unknown="UNSURE")
    def switch(is_on):
        return "ON"

    color, state = rules.registered_rules()
    assert (color.channel, color.target, color.callback) == ("level", "TANK", tank)
    assert color.element_ids == {"TANK"}
    assert (state.channel, state.unknown) == ("switch", "UNSURE")
    assert state.element_ids == {"ON", "OFF", "UNSURE"}
    assert tank(1) == GREEN  # the decorated function stays usable


@pytest.mark.parametrize(
    "value, expected", [(5, "low"), (10, "low"), (10.001, "mid"), (20, "mid"), (21, "high")]
)
def test_bands(value, expected):
    assert bands(value, [(10, "low"), (20, "mid")], above="high") == expected


def test_unknown_before_connecting(view):
    RuleBinding(ColorRule("level", "TANK", lambda level: GREEN), view)
    assert_unknown_color(view)


def test_unknown_without_a_value(view):
    color_binding(view)
    assert_unknown_color(view)


def test_known_value(view):
    binding = color_binding(view)
    binding.value_changed(5.0)
    assert_known_color(view, GREEN)
    binding.value_changed(50)
    assert_known_color(view, RED)


def test_unknown_when_disconnected(view):
    binding = color_binding(view)
    binding.value_changed(5.0)
    binding.connection_changed(False)
    assert_unknown_color(view)


def test_old_value_is_not_used_after_reconnecting(view):
    binding = color_binding(view)
    binding.value_changed(5.0)
    binding.connection_changed(False)
    binding.connection_changed(True)
    assert_unknown_color(view)
    binding.value_changed(5.0)
    assert_known_color(view, GREEN)


def test_unknown_with_invalid_severity(view):
    binding = color_binding(view)
    binding.value_changed(5.0)
    binding.severity_changed(INVALID_SEVERITY)
    assert_unknown_color(view)
    binding.severity_changed(0)
    assert_known_color(view, GREEN)


def test_alarm_severity_is_still_known(view):
    binding = color_binding(view)
    binding.value_changed(5.0)
    binding.severity_changed(ALARM_SEVERITY)
    assert_known_color(view, GREEN)


@pytest.mark.parametrize("value", [math.nan, np.float64("nan"), "5.0", True, np.array([1.0, 2.0]), None])
def test_color_rule_unknown_values(view, value):
    binding = color_binding(view)
    binding.value_changed(5.0)
    binding.value_changed(value)
    assert_unknown_color(view)


@pytest.mark.parametrize("value", [5, 5.0, np.float64(5.0), np.int32(5), -math.inf])
def test_color_rule_usable_values(view, value):
    binding = color_binding(view)
    binding.value_changed(value)
    assert_known_color(view, GREEN)


@pytest.mark.parametrize("value, shown", [(True, "ON"), (False, "OFF"), (1, "ON"), (0, "OFF")])
def test_state_rule_usable_values(view, value, shown):
    binding = state_binding(view)
    binding.value_changed(value)
    assert view.shown() == {shown}


@pytest.mark.parametrize("value", [2, -1, 1.0, "True", math.nan])
def test_state_rule_unknown_values(view, value):
    binding = state_binding(view)
    binding.value_changed(True)
    binding.value_changed(value)
    assert view.shown() == {"UNSURE"}


def test_state_rule_shows_exactly_one_asset(view):
    binding = state_binding(view)
    assert view.shown() == {"UNSURE"}
    binding.value_changed(True)
    assert view.visible == {"ON": True, "OFF": False, "UNSURE": False}
    binding.value_changed(False)
    assert view.visible == {"ON": False, "OFF": True, "UNSURE": False}
    assert view.hatched == set()


def test_state_rule_rejects_undeclared_asset(view, caplog):
    binding = state_binding(view, callback=lambda is_on: "SOMETHING_ELSE")
    binding.value_changed(True)
    assert view.shown() == {"UNSURE"}
    assert "SOMETHING_ELSE" in caplog.text


def test_failing_callback_shows_unknown(view, caplog):
    binding = RuleBinding(ColorRule("level", "TANK", lambda level: 1 / 0), view)
    binding.connection_changed(True)
    binding.value_changed(5.0)
    assert_unknown_color(view)
    assert "level" in caplog.text


# --- MAXI rules ---


def test_maxi_rules_are_registered():
    channels = {rule.channel for rule in rules.registered_rules()}
    assert {"chamber_pressure", "detector_temperature", "valve_open", "shutter_open"} <= channels


@pytest.mark.parametrize(
    "pressure, color", [(3e-7, GREEN), (5e-6, GREEN), (1e-3, YELLOW), (700, YELLOW), (1013, GRAY)]
)
def test_chamber_color(view, pressure, color):
    bind("chamber_pressure", view, pressure)
    assert_known_color(view, color, "MAXICHAMBER")


def test_chamber_with_alarm_quality(view):
    binding = bind("chamber_pressure", view, 1e-6)
    binding.severity_changed(ALARM_SEVERITY)
    assert_known_color(view, GREEN, "MAXICHAMBER")


def test_chamber_disconnects_and_recovers(view):
    binding = bind("chamber_pressure", view, 3e-7)
    binding.connection_changed(False)
    assert_unknown_color(view, "MAXICHAMBER")
    binding.connection_changed(True)
    binding.value_changed(3e-7)
    assert_known_color(view, GREEN, "MAXICHAMBER")


@pytest.mark.parametrize("temperature, color", [(-40, BLUE), (15, BLUE), (22, GRAY)])
def test_detector_color(view, temperature, color):
    bind("detector_temperature", view, temperature)
    assert_known_color(view, color, "DETECTOR")


def test_valve_open(view):
    bind("valve_open", view, True)
    assert view.shown() == {"VALVE_OPEN"}


def test_valve_closed(view):
    bind("valve_open", view, 0)
    assert view.shown() == {"VALVE_CLOSED"}


def test_valve_disconnected(view):
    binding = bind("valve_open", view, True)
    binding.connection_changed(False)
    assert view.shown() == {"VALVE_UNKNOWN"}


def test_shutter_closed(view):
    bind("shutter_open", view, False)
    assert view.shown() == {"SHUTTER_CLOSED"}


def test_shutter_open(view):
    bind("shutter_open", view, 1)
    assert view.shown() == {"SHUTTER_OPEN"}


def test_shutter_invalid(view):
    binding = bind("shutter_open", view, False)
    binding.severity_changed(INVALID_SEVERITY)
    assert view.shown() == {"SHUTTER_UNKNOWN"}


def test_colors_are_distinct():
    colors = {maxi_rules.GREEN, maxi_rules.YELLOW, maxi_rules.BLUE, maxi_rules.GRAY}
    assert len(colors) == 4
    # vented and unknown share one gray; only the hatching tells them apart
    assert maxi_rules.GRAY == UNKNOWN_COLOR


# --- rules on the real SVG ---

STATE_ASSETS = (
    "VALVE_OPEN",
    "VALVE_CLOSED",
    "VALVE_UNKNOWN",
    "SHUTTER_OPEN",
    "SHUTTER_CLOSED",
    "SHUTTER_UNKNOWN",
)


def visible_assets(svg_view):
    return {asset for asset in STATE_ASSETS if svg_view.is_visible(asset)}


@pytest.fixture
def maxi_dom():
    dom = SvgDom.from_file(MAXI_SVG)
    # As if the file had been saved in Inkscape with other assets and colors showing
    dom.set_style("VALVE_OPEN", "display", "inline")
    dom.set_style("VALVE_UNKNOWN", "display", "none")
    dom.set_style("SHUTTER_UNKNOWN", "display", "none")
    return dom


@pytest.fixture
def maxi_view(qtbot, maxi_dom):
    svg_view = SvgView(maxi_dom)
    qtbot.addWidget(svg_view)
    return svg_view


def test_startup_shows_only_unknown_assets(maxi_view):
    assert visible_assets(maxi_view) == {"VALVE_OPEN"}
    for rule in rules.registered_rules():
        RuleBinding(rule, maxi_view)
    assert visible_assets(maxi_view) == {"VALVE_UNKNOWN", "SHUTTER_UNKNOWN"}
    assert maxi_view.hatched() == {"MAXICHAMBER", "DETECTOR"}
    assert maxi_view.fill("MAXICHAMBER") == UNKNOWN_COLOR
    assert maxi_view.fill("DETECTOR") == UNKNOWN_COLOR


def test_rules_change_the_svg(maxi_view):
    bindings = {rule.channel: RuleBinding(rule, maxi_view) for rule in rules.registered_rules()}
    for binding in bindings.values():
        binding.connection_changed(True)
    bindings["chamber_pressure"].value_changed(3e-7)
    bindings["valve_open"].value_changed(1)
    assert maxi_view.fill("MAXICHAMBER") == GREEN
    assert maxi_view.hatched() == {"DETECTOR"}
    assert visible_assets(maxi_view) == {"VALVE_OPEN", "SHUTTER_UNKNOWN"}
