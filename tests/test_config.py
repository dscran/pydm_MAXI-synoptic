import pytest

from synoptic import config as cfg
from synoptic.config import ConfigError, PlotEntry, ValueFormat, parse_config, parse_format, resolve_address


def errors_of(data):
    _, errors = parse_config(data)
    return errors


def assert_one_error(errors, *fragments):
    assert len(errors) == 1, errors
    for fragment in fragments:
        assert fragment in errors[0]


def test_valid_config():
    config, errors = parse_config(
        {
            "defaults": {"tango_host": "maxi-ctrl:10000", "tango_poll_period": 0.5, "max_redraw_rate": 5},
            "values": {"A_value": {"source": "a/b/c/d", "format": "%.2e"}},
            "plots": {
                "A_plot": {
                    "source": "a/b/c/d",
                    "refresh_period": 1.0,
                    "log_y": True,
                    "time_span": 3600,
                    "y_range": [1e-9, 1000],
                }
            },
            "extra_channels": {"valve_open": "maxi/vac/valve1/is_open"},
        }
    )
    assert errors == []
    assert config.defaults.tango_poll_period == 0.5
    assert config.defaults.max_redraw_rate == 5
    assert config.values["A_value"].format == ValueFormat(cfg.EXPONENTIAL, 2)
    assert config.plots["A_plot"] == PlotEntry("a/b/c/d", 1.0, True, 3600.0, (1e-9, 1000.0))
    assert config.extra_channels == {"valve_open": "maxi/vac/valve1/is_open"}


def test_plot_defaults():
    config, errors = parse_config({"plots": {"A_plot": {"source": "a/b/c/d", "refresh_period": 2}}})
    assert errors == []
    plot = config.plots["A_plot"]
    assert plot.time_span == 600.0
    assert plot.log_y is False
    assert plot.y_range is None


@pytest.mark.parametrize("data", [None, {}, {"values": None}, {"values": {"A_value": {"source": "a/b/c/d"}}}])
def test_missing_sections_are_empty(data):
    config, errors = parse_config(data)
    assert errors == []
    assert config.plots == {}
    assert config.extra_channels == {}
    assert config.defaults.tango_host is None
    assert config.defaults.max_redraw_rate is None


def test_unknown_top_level_key():
    assert_one_error(errors_of({"value": {}}), "unknown top-level key", "'value'")


@pytest.mark.parametrize(
    "data, where",
    [
        ({"values": {"A_value": {"source": "a/b/c/d", "fromat": "%d"}}}, "values.A_value"),
        ({"plots": {"A_plot": {"source": "a/b/c/d", "refresh_period": 1, "logy": True}}}, "plots.A_plot"),
        ({"defaults": {"host": "x"}}, "defaults"),
    ],
)
def test_unknown_entry_key(data, where):
    assert_one_error(errors_of(data), where, "unknown key")


def test_value_without_source():
    assert_one_error(errors_of({"values": {"A_value": {"format": "%.2e"}}}), "values.A_value", "'source'")


def test_plot_without_refresh_period():
    assert_one_error(
        errors_of({"plots": {"A_plot": {"source": "a/b/c/d"}}}), "plots.A_plot", "'refresh_period'"
    )


@pytest.mark.parametrize("key", ["refresh_period", "time_span"])
@pytest.mark.parametrize("number", [0, -1.5, "fast", True])
def test_non_positive_plot_number(key, number):
    entry = {"source": "a/b/c/d", "refresh_period": 1.0, key: number}
    assert_one_error(errors_of({"plots": {"A_plot": entry}}), "plots.A_plot", key)


@pytest.mark.parametrize("number", [0, -2])
def test_non_positive_poll_period(number):
    assert_one_error(errors_of({"defaults": {"tango_poll_period": number}}), "defaults", "tango_poll_period")


@pytest.mark.parametrize("number", [0, -1, 2.5, "fast", True])
def test_invalid_max_redraw_rate(number):
    assert_one_error(errors_of({"defaults": {"max_redraw_rate": number}}), "defaults", "max_redraw_rate")


@pytest.mark.parametrize("y_range", [[1, 1], [5, 2], [1], [1, 2, 3], 5, ["1e-9", "1e3"], [True, 2], "auto"])
def test_invalid_y_range(y_range):
    entry = {"source": "a/b/c/d", "refresh_period": 1.0, "y_range": y_range}
    assert_one_error(errors_of({"plots": {"A_plot": entry}}), "plots.A_plot", "y_range")


@pytest.mark.parametrize("lowest", [0, -5])
def test_log_y_range_must_be_positive(lowest):
    entry = {"source": "a/b/c/d", "refresh_period": 1.0, "log_y": True, "y_range": [lowest, 10]}
    assert_one_error(errors_of({"plots": {"A_plot": entry}}), "plots.A_plot", "y_range", "log_y")


def test_linear_y_range_may_be_negative():
    entry = {"source": "a/b/c/d", "refresh_period": 1.0, "y_range": [-40, 30]}
    config, errors = parse_config({"plots": {"A_plot": entry}})
    assert errors == []
    assert config.plots["A_plot"].y_range == (-40.0, 30.0)


def test_exponent_without_dot_is_reported(tmp_path):
    # YAML reads 1e-9 as text; the error must show that
    path = tmp_path / "config.yaml"
    path.write_text(
        "plots:\n  A_plot:\n    source: a/b/c/d\n    refresh_period: 1\n    y_range: [1e-9, 1e3]\n"
    )
    _, errors = cfg.load_config(path)
    assert_one_error(errors, "y_range", "'1e-9'")


def test_errors_are_collected():
    errors = errors_of(
        {
            "value": {},
            "values": {"A_value": {"format": "6.3f"}},
            "plots": {"A_plot": {"source": "a/b/c/d", "refresh_period": 0}},
        }
    )
    assert len(errors) == 4  # unknown key, missing source, invalid format, refresh_period


def test_entry_with_error_keeps_its_id():
    config, _ = parse_config({"values": {"A_value": {}}})
    assert "A_value" in config.values


# --- Tango address resolution ---


def test_address_with_tango_host():
    config, _ = parse_config({"defaults": {"tango_host": "maxi-ctrl:10000"}})
    assert config.address("maxi/vac/gauge1/pressure") == "tango://maxi-ctrl:10000/maxi/vac/gauge1/pressure"


def test_address_without_tango_host():
    assert resolve_address("maxi/vac/gauge1/pressure") == "tango://maxi/vac/gauge1/pressure"


@pytest.mark.parametrize("tango_host", [None, "maxi-ctrl:10000"])
def test_full_address_is_unchanged(tango_host):
    address = "tango://other:10000/a/b/c/attr"
    assert resolve_address(address, tango_host) == address


# --- printf formats ---


@pytest.mark.parametrize(
    "text, expected",
    [
        ("%.2e", ValueFormat(cfg.EXPONENTIAL, 2)),
        ("%6.3f", ValueFormat(cfg.DECIMAL, 3)),
        ("%d", ValueFormat(cfg.DECIMAL, 0)),
        ("%s", ValueFormat(cfg.STRING, None)),
        ("%f", ValueFormat(cfg.DECIMAL, 6)),
    ],
)
def test_parse_format(text, expected):
    assert parse_format(text) == expected


@pytest.mark.parametrize("text", ["6.3f", "%", "%.2e mbar", ""])
def test_parse_format_invalid(text):
    with pytest.raises(ValueError, match="invalid format"):
        parse_format(text)


def test_invalid_format_names_entry_and_format():
    errors = errors_of({"values": {"A_value": {"source": "a/b/c/d", "format": "6.3f"}}})
    assert_one_error(errors, "values.A_value", "'6.3f'")


# --- YAML files ---


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_load_config(tmp_path):
    path = write(tmp_path, 'values:\n  A_value:\n    source: a/b/c/d\n    format: "%6.3f"\n')
    config, errors = cfg.load_config(path)
    assert errors == []
    assert config.values["A_value"].format == ValueFormat(cfg.DECIMAL, 3)


def test_unquoted_format_reports_line_and_hint(tmp_path):
    path = write(tmp_path, "values:\n  A_value:\n    source: a/b/c/d\n    format: %6.3f\n")
    _, errors = cfg.load_config(path)
    assert_one_error(errors, "line 4, column 13", "must be quoted")


def test_other_yaml_error_has_no_hint(tmp_path):
    _, errors = cfg.load_config(write(tmp_path, "values: [1, 2\n"))
    assert_one_error(errors, "YAML syntax error at line")
    assert "quoted" not in errors[0]


def test_missing_file(tmp_path):
    _, errors = cfg.load_config(tmp_path / "nothing.yaml")
    assert_one_error(errors, "nothing.yaml")


# --- config file lookup ---


def test_default_config_path(tmp_path):
    display_file = tmp_path / "maxi_synoptic.py"
    assert cfg.config_path(display_file) == tmp_path / "maxi_synoptic.yaml"
    assert cfg.config_path(display_file, {"other": "x"}) == tmp_path / "maxi_synoptic.yaml"


def test_config_path_from_macro(tmp_path):
    display_file = tmp_path / "maxi_synoptic.py"
    assert cfg.config_path(display_file, {"config": "other.yaml"}) == tmp_path / "other.yaml"


def test_config_error_lists_all_errors():
    error = ConfigError(["first problem", "second problem"])
    assert "first problem" in str(error)
    assert "second problem" in str(error)
