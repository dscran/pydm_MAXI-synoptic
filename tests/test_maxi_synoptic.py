import logging
from pathlib import Path

import pytest
import yaml
from qtpy.QtGui import QColor, QPalette

import maxi_synoptic
from maxi_synoptic import MaxiSynoptic
from sim.maxi_sim import DEFAULT_PORT, panel_config
from synoptic.config import ConfigError, load_config
from synoptic.rules import registered_rules
from synoptic.svg_view import SvgDom
from synoptic.validation import validate

REPO_DIR = Path(__file__).parent.parent
# Nothing listens here, so every channel stays disconnected
UNREACHABLE = "localhost:1"
NUM_VALUE_SLOTS = 20
NUM_PLOT_SLOTS = 3
NUM_RULES = 6
NUM_RULE_CHANNELS = 4
# as set in maxi_synoptic.qss
VALUE_FONT_PX = 30
VALUE_COLOR = "#f2f4f7"


def write_config(tmp_path, data):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data))
    return {"config": str(path)}


@pytest.fixture
def display(qtbot, tmp_path):
    display = MaxiSynoptic(macros=write_config(tmp_path, panel_config(UNREACHABLE)))
    qtbot.addWidget(display)
    display.resize(1920, 1080)
    display.show()
    qtbot.waitExposed(display)
    return display


def validate_file(file_name):
    config, config_errors = load_config(REPO_DIR / file_name)
    svg_ids = SvgDom.from_file(maxi_synoptic.SVG_FILE).ids()
    errors, warnings = validate(config, svg_ids, registered_rules())
    return config, config_errors + errors, warnings


def test_display_is_built_from_config(display):
    assert len(display.overlays.labels) == NUM_VALUE_SLOTS
    assert len(display.overlays.plots) == NUM_PLOT_SLOTS
    assert len(display.rule_bindings) == NUM_RULES
    assert display.view.size() == display.size()


def test_style_sheet_sets_value_font_and_color(qtbot, qapp, tmp_path):
    theme = qapp.palette()
    other_theme = QPalette(theme)
    other_theme.setColor(QPalette.WindowText, QColor("#ff0000"))
    qapp.setPalette(other_theme)
    try:
        display = MaxiSynoptic(macros=write_config(tmp_path, panel_config(UNREACHABLE)))
        qtbot.addWidget(display)
        display.show()
        qtbot.waitExposed(display)
        label = display.overlays.labels[0]
        assert label.fontInfo().pixelSize() == VALUE_FONT_PX
        assert label.palette().color(QPalette.WindowText).name() == VALUE_COLOR
    finally:
        qapp.setPalette(theme)


def test_font_does_not_scale_with_the_window(qtbot, display):
    label = display.overlays.labels[0]
    display.resize(960, 540)
    qtbot.waitUntil(lambda: display.view.scale() == pytest.approx(0.5), timeout=10000)
    assert label.height() == round(display.view.element_rect("DIODE_current_value").height())
    assert label.fontInfo().pixelSize() == VALUE_FONT_PX


def test_redraw_rate_from_config(qtbot, tmp_path):
    data = {**panel_config(UNREACHABLE), "defaults": {"max_redraw_rate": 4}}
    display = MaxiSynoptic(macros=write_config(tmp_path, data))
    qtbot.addWidget(display)
    assert [plot.maxRedrawRate for plot in display.overlays.plots] == [4, 4, 4]


def test_display_starts_with_unknown_looks(display):
    view = display.view
    assert view.is_visible("VALVE_UNKNOWN") and view.is_visible("SHUTTER_UNKNOWN")
    for asset in ("VALVE_OPEN", "VALVE_CLOSED", "SHUTTER_OPEN", "SHUTTER_CLOSED"):
        assert not view.is_visible(asset)
    assert view.hatched() == {"MAXICHAMBER", "DETECTOR"}


def test_no_widget_can_write(display):
    for label in display.overlays.labels:
        assert not hasattr(label, "send_value")
    for binding in display.rule_bindings:
        assert binding._channel.value_signal is None


def test_missing_sections_give_an_empty_panel(qtbot, tmp_path, caplog):
    extra_channels = panel_config(UNREACHABLE)["extra_channels"]
    display = MaxiSynoptic(macros=write_config(tmp_path, {"extra_channels": extra_channels}))
    qtbot.addWidget(display)
    assert display.overlays.labels == []
    assert display.overlays.plots == []
    assert "'DIODE_encoder_value' is not configured" in caplog.text


def test_invalid_config_lists_every_error(tmp_path, caplog):
    data = panel_config(UNREACHABLE)
    data["values"]["MAXI_VAC_presure_value"] = {"source": "a/b/c/d"}
    data["values"]["NO_SUCH_value"] = {"source": "a/b/c/d"}
    del data["values"]["DIODE_current_value"]["source"]
    del data["extra_channels"]["shutter_open"]
    with pytest.raises(ConfigError) as failure:
        MaxiSynoptic(macros=write_config(tmp_path, data))
    errors = failure.value.errors
    assert len(errors) == 4
    message = str(failure.value)
    assert "no SVG element with id 'MAXI_VAC_presure_value'" in message
    assert "no SVG element with id 'NO_SUCH_value'" in message
    assert "DIODE_current_value: missing 'source'" in message
    assert "'shutter_open'" in message
    logged_errors = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert len(logged_errors) == 4


def test_unquoted_format_stops_startup(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("values:\n  DIODE_current_value:\n    source: a/b/c/d\n    format: %6.3f\n")
    with pytest.raises(ConfigError, match="line 4.*must be quoted"):
        MaxiSynoptic(macros={"config": str(path)})


def test_missing_asset_stops_startup(tmp_path, monkeypatch):
    svg_text = maxi_synoptic.SVG_FILE.read_text().replace('id="SHUTTER_UNKNOWN"', 'id="SHUTTER_OTHER"')
    svg_file = tmp_path / "changed.svg"
    svg_file.write_text(svg_text)
    monkeypatch.setattr(maxi_synoptic, "SVG_FILE", svg_file)
    with pytest.raises(ConfigError, match="no SVG element with id 'SHUTTER_UNKNOWN'"):
        MaxiSynoptic(macros=write_config(tmp_path, panel_config(UNREACHABLE)))


# --- the configuration files of the repository ---


@pytest.mark.parametrize("file_name", ["maxi_synoptic.yaml", "maxi_synoptic_sim.yaml"])
def test_config_file_is_valid_and_complete(file_name):
    config, errors, warnings = validate_file(file_name)
    assert errors == []
    assert warnings == []
    assert len(config.values) == NUM_VALUE_SLOTS
    assert len(config.plots) == NUM_PLOT_SLOTS
    assert len(config.extra_channels) == NUM_RULE_CHANNELS


def test_placeholders_are_marked():
    lines = (REPO_DIR / "maxi_synoptic.yaml").read_text().splitlines()
    unmarked = [
        line
        for line in lines
        if "maxi/" in line and not line.lstrip().startswith("#") and "PLACEHOLDER" not in line
    ]
    assert unmarked == []


def test_sim_config_matches_the_simulator():
    data = yaml.safe_load((REPO_DIR / "maxi_synoptic_sim.yaml").read_text())
    assert data == panel_config(f"localhost:{DEFAULT_PORT}")
