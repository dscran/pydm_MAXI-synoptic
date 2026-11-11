from dataclasses import dataclass

from synoptic.config import parse_config
from synoptic.validation import validate

SVG_IDS = {"A_value", "B_value", "A_plot", "DATETIME_value", "TANK", "ON", "OFF", "UNSURE", "A_label"}


@dataclass(frozen=True)
class FakeRule:
    channel: str
    element_ids: frozenset


TANK_RULE = FakeRule("level", frozenset({"TANK"}))
SWITCH_RULE = FakeRule("switch", frozenset({"ON", "OFF", "UNSURE"}))

VALID = {
    "values": {"A_value": {"source": "a/b/c/d"}, "B_value": {"source": "a/b/c/e"}},
    "plots": {"A_plot": {"source": "a/b/c/d", "refresh_period": 1}},
    "extra_channels": {"level": "a/b/c/level", "switch": "a/b/c/switch"},
}


def check(data, svg_ids=SVG_IDS, rules=(TANK_RULE, SWITCH_RULE)):
    config, schema_errors = parse_config(data)
    errors, warnings = validate(config, set(svg_ids), rules)
    return schema_errors + errors, warnings


def changed(section, entries):
    return {**VALID, section: entries}


def test_valid_config():
    assert check(VALID) == ([], [])


def test_value_id_not_in_svg():
    errors, _ = check(changed("values", {**VALID["values"], "A_presure_value": {"source": "a/b/c/d"}}))
    assert errors == ["values.A_presure_value: no SVG element with id 'A_presure_value'"]


def test_plot_id_not_in_svg():
    errors, _ = check(
        changed("plots", {"C_plot": {"source": "a/b/c/d", "refresh_period": 1}}), SVG_IDS - {"A_plot"}
    )
    assert errors == ["plots.C_plot: no SVG element with id 'C_plot'"]


def test_id_in_values_and_plots():
    errors, _ = check(changed("values", {**VALID["values"], "A_plot": {"source": "a/b/c/d"}}))
    assert len(errors) == 1
    assert "'A_plot'" in errors[0]
    assert "both" in errors[0]


def test_rule_element_not_in_svg():
    errors, _ = check(VALID, SVG_IDS - {"UNSURE"})
    assert len(errors) == 1
    assert "no SVG element with id 'UNSURE'" in errors[0]


def test_rule_channel_not_in_extra_channels():
    errors, _ = check(changed("extra_channels", {"level": "a/b/c/level"}))
    assert len(errors) == 1
    assert "'switch'" in errors[0]


def test_missing_channel_of_several_rules_is_reported_once():
    second_rule = FakeRule("switch", frozenset({"ON"}))
    errors, _ = check(
        changed("extra_channels", {"level": "a/b/c/level"}), rules=(TANK_RULE, SWITCH_RULE, second_rule)
    )
    assert len(errors) == 1


def test_unconfigured_slots_give_warnings():
    errors, warnings = check(changed("values", {"A_value": {"source": "a/b/c/d"}}), SVG_IDS | {"C_plot"})
    assert errors == []
    assert len(warnings) == 2
    assert any("'B_value'" in warning for warning in warnings)
    assert any("'C_plot'" in warning for warning in warnings)


def test_clock_and_other_elements_need_no_configuration():
    _, warnings = check(VALID)
    assert not any("DATETIME_value" in warning or "A_label" in warning for warning in warnings)


def test_unused_extra_channel_gives_warning():
    errors, warnings = check(
        changed("extra_channels", {**VALID["extra_channels"], "spare_gauge": "a/b/c/spare"})
    )
    assert errors == []
    assert len(warnings) == 1
    assert "'spare_gauge'" in warnings[0]


def test_several_errors_are_reported_together():
    data = changed(
        "values",
        {
            "X_value": {"source": "a/b/c/d"},
            "Y_value": {"source": "a/b/c/d"},
            "A_value": {"format": "%.2e"},
            "B_value": {"source": "a/b/c/e"},
        },
    )
    errors, _ = check(data)
    assert len(errors) == 3
    assert any("X_value" in error for error in errors)
    assert any("Y_value" in error for error in errors)
    assert any("A_value" in error and "'source'" in error for error in errors)
