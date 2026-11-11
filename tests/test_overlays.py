import re
from pathlib import Path

import pytest
from pydm.widgets.timeplot import UpdateMode
from qtpy.QtCore import QRect

from synoptic import config as cfg
from synoptic.config import PlotEntry, ValueFormat
from synoptic.overlays import Overlays, value_axis
from synoptic.svg_view import SvgDom, SvgView

# SLOT_value is at (1030, 150) after its transforms, 200x40. FIX_plot is at (100, 700), 400x200.
FIXTURE = Path(__file__).parent / "fixture.svg"


def make_view(qtbot):
    view = SvgView(SvgDom.from_file(FIXTURE))
    qtbot.addWidget(view)
    view.resize(1920, 1080)
    view.show()
    qtbot.waitExposed(view)
    return view


@pytest.fixture
def view(qtbot):
    return make_view(qtbot)


@pytest.fixture
def overlays(view):
    return Overlays(view)


def local_channel(name, init):
    return f"loc://{name}?type=float&init={init}"


# --- value labels ---


def test_label_covers_its_transformed_slot(overlays):
    label = overlays.add_value("SLOT_value", local_channel("placed", 1.0))
    assert label.geometry() == QRect(1030, 150, 200, 40)
    assert label.isVisible()


def test_label_follows_resize(qtbot, view, overlays):
    label = overlays.add_value("SLOT_value", local_channel("resized", 1.0))
    view.resize(960, 540)
    qtbot.waitUntil(lambda: label.geometry() == QRect(515, 75, 100, 20), timeout=2000)


def test_label_settings(overlays):
    label = overlays.add_value("SLOT_value", local_channel("settings", 1.0))
    assert label.alarmSensitiveBorder is True
    assert label.showUnits is True
    assert label.precisionFromPV is True


def feed(label, value):
    """Give a label a value directly, as its channel would."""
    label.connectionStateChanged(True)
    label.value_changed(value)


def test_format_override(overlays):
    address = local_channel("exponent", 0)
    label = overlays.add_value("SLOT_value", address, ValueFormat(cfg.EXPONENTIAL, 2))
    feed(label, 0.000012345)
    assert label.text() == "1.23e-05"
    assert label.precisionFromPV is False


def test_decimal_format_override(overlays):
    label = overlays.add_value("SLOT_value", local_channel("decimal", 0), ValueFormat(cfg.DECIMAL, 3))
    label.precisionChanged(1)  # the precision of the channel must not win over the format
    feed(label, 1.23456)
    assert label.text() == "1.235"


def test_channel_precision_without_format(overlays):
    label = overlays.add_value("SLOT_value", local_channel("tango_format", 0))
    label.precisionChanged(3)  # as the Tango plugin sends it for the Tango format %6.3f
    feed(label, 1.23456)
    assert label.text() == "1.235"


def test_unit_is_shown(overlays):
    label = overlays.add_value("SLOT_value", local_channel("unit", 0), ValueFormat(cfg.DECIMAL, 1))
    label.unitChanged("mbar")
    feed(label, 3.0)
    assert label.text() == "3.0 mbar"


def test_disconnected_label_is_disabled(overlays):
    label = overlays.add_value("SLOT_value", local_channel("disconnected", 0))
    feed(label, 1.0)
    label.connectionStateChanged(False)
    assert not label.isEnabled()


# --- plots ---


def test_plot_with_all_options(overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=2.0, log_y=True, time_span=3600.0)
    plot = overlays.add_plot("FIX_plot", local_channel("plot_all", 1.0), entry)
    assert plot.updateMode == UpdateMode.AtFixedRate
    assert plot.updateInterval == 2.0
    assert plot.timeSpan == 3600.0
    assert value_axis(plot).log_mode is True
    assert plot.backgroundBrush().color().name() == "#ffffff"
    assert plot.getAxisColor().lightness() < 127
    assert len(plot.curves) == 1


def test_plot_takes_the_colors_of_a_dark_slot(view, overlays):
    view.set_fill("FIX_plot", "#15181c")
    plot = overlays.add_plot(
        "FIX_plot", local_channel("plot_dark", 1.0), PlotEntry("a/b/c/d", refresh_period=1.0)
    )
    assert plot.backgroundBrush().color().name() == "#15181c"
    assert plot.getAxisColor().lightness() > 127


def y_view_range(plot):
    return value_axis(plot).linkedView().viewRange()[1]


def test_plot_with_fixed_linear_range(qtbot, overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=0.1, y_range=(-40.0, 30.0))
    plot = overlays.add_plot("FIX_plot", local_channel("plot_fixed", 500.0), entry)
    assert value_axis(plot).auto_range is False
    assert y_view_range(plot) == pytest.approx([-40, 30])
    # values outside of the range must not move the axis
    qtbot.waitUntil(lambda: plot.curveAtIndex(0).points_accumulated >= 3, timeout=3000)
    qtbot.wait(1200)  # at least one redraw
    assert y_view_range(plot) == pytest.approx([-40, 30])


def test_plot_with_fixed_log_range(overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=1.0, log_y=True, y_range=(1e-9, 1e3))
    plot = overlays.add_plot("FIX_plot", local_channel("plot_fixed_log", 1.0), entry)
    assert y_view_range(plot) == pytest.approx([-9, 3])


def test_plot_with_defaults(overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=1.0)
    plot = overlays.add_plot("FIX_plot", local_channel("plot_defaults", 1.0), entry)
    assert plot.updateMode == UpdateMode.AtFixedRate
    assert plot.updateInterval == 1.0
    assert plot.timeSpan == 600.0
    assert value_axis(plot).log_mode is False
    assert value_axis(plot).auto_range is True
    assert plot.maxRedrawRate == 1  # PyDM's default


def test_plot_redraw_rate(overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=0.2)
    plot = overlays.add_plot("FIX_plot", local_channel("plot_redraw", 1.0), entry, max_redraw_rate=5)
    assert plot.maxRedrawRate == 5
    assert plot.redraw_timer.interval() == 200


def test_plot_covers_its_slot(qtbot, view, overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=1.0)
    plot = overlays.add_plot("FIX_plot", local_channel("plot_placed", 1.0), entry)
    assert plot.geometry() == QRect(100, 700, 400, 200)
    view.resize(960, 540)
    qtbot.waitUntil(lambda: plot.geometry() == QRect(50, 350, 200, 100), timeout=2000)


def test_plot_adds_points_for_a_constant_value(qtbot, overlays):
    entry = PlotEntry("a/b/c/d", refresh_period=0.1)
    plot = overlays.add_plot("FIX_plot", local_channel("plot_constant", 5.0), entry)
    curve = plot.curveAtIndex(0)
    qtbot.waitUntil(lambda: curve.points_accumulated >= 5, timeout=3000)


# --- clock ---


def test_clock(qtbot, overlays):
    clock = overlays.add_clock("DATETIME_value")
    assert clock.geometry() == QRect(24, 1016, 340, 40)
    first_text = clock.text()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", first_text)
    qtbot.waitUntil(lambda: clock.text() != first_text, timeout=2500)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", clock.text())
