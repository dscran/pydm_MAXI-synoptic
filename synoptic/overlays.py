"""Widgets placed over slots of the SVG: value labels, time plots and the clock.

Fonts and colors of the labels and the clock are not set here. They come from a Qt style sheet.
"""

from __future__ import annotations

import math
from datetime import datetime

from pydm.widgets import PyDMLabel, PyDMTimePlot
from pydm.widgets.display_format import DisplayFormat
from pydm.widgets.timeplot import UpdateMode
from qtpy.QtCore import QObject, Qt, QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QLabel, QWidget

from synoptic import config as cfg
from synoptic.config import PlotEntry, ValueFormat
from synoptic.svg_view import SvgView

CLOCK_FORMAT = "%Y-%m-%d %H:%M:%S"
CLOCK_PERIOD_MS = 1000
FALLBACK_PLOT_BACKGROUND = "#ffffff"
DARK_FOREGROUND = "#2e3436"
LIGHT_FOREGROUND = "#d3d9df"
# Qt's lightness goes from 0 to 255
DARK_BACKGROUND_MAX_LIGHTNESS = 127
PLOT_AXIS_NAME = "value"

DISPLAY_FORMATS = {
    cfg.EXPONENTIAL: DisplayFormat.Exponential,
    cfg.DECIMAL: DisplayFormat.Decimal,
    cfg.STRING: DisplayFormat.String,
}


class ClockLabel(QLabel):
    """Shows the local date and time."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._timer = QTimer(self)
        self._timer.setInterval(CLOCK_PERIOD_MS)
        self._timer.timeout.connect(self.show_time)
        self._timer.start()
        self.show_time()

    def show_time(self) -> None:
        self.setText(datetime.now().strftime(CLOCK_FORMAT))


class Overlays(QObject):
    """Creates the overlay widgets of an SvgView and keeps them on their SVG elements when it resizes."""

    def __init__(self, view: SvgView):
        super().__init__(view)
        self._view = view
        self._slot_of_widget = {}
        self.labels: list[PyDMLabel] = []
        self.plots: list[PyDMTimePlot] = []
        view.resized.connect(self.place_all)

    def add_value(self, element_id: str, address: str, value_format: ValueFormat | None = None) -> PyDMLabel:
        """Show a channel as text over an SVG element. A `value_format` overrides the channel's precision."""
        label = PyDMLabel(parent=self._view, init_channel=address)
        label.setAlignment(Qt.AlignCenter)
        label.alarmSensitiveBorder = True
        label.alarmSensitiveContent = False
        label.showUnits = True
        if value_format is not None:
            _apply_format(label, value_format)
        self.labels.append(label)
        self._place_on(element_id, label)
        return label

    def add_plot(
        self, element_id: str, address: str, entry: PlotEntry, max_redraw_rate: int | None = None
    ) -> PyDMTimePlot:
        """Plot a channel over time over an SVG element. Without `max_redraw_rate` (Hz), PyDM's default is kept."""
        # The plot takes the color of its slot, so that it fits into light and dark SVGs
        background = QColor(self._view.fill(element_id) or FALLBACK_PLOT_BACKGROUND)
        foreground = _foreground_on(background)
        plot = PyDMTimePlot(parent=self._view, background=background)
        plot.setAxisColor(foreground)
        plot.setShowLegend(False)
        if max_redraw_rate is not None:
            plot.maxRedrawRate = max_redraw_rate
        # A fixed rate adds a point every period, so a value that never changes still draws a line.
        # These are set before the curve is added, because the curve takes its buffer size from them.
        plot.updateMode = UpdateMode.AtFixedRate
        plot.updateInterval = entry.refresh_period
        plot.timeSpan = entry.time_span
        plot.addYChannel(y_channel=address, yAxisName=PLOT_AXIS_NAME, color=foreground)
        value_axis(plot).setLabel("")
        value_axis(plot).log_mode = entry.log_y
        if entry.y_range is not None:
            _fix_y_range(value_axis(plot), entry.y_range, entry.log_y)
        self.plots.append(plot)
        self._place_on(element_id, plot)
        return plot

    def add_clock(self, element_id: str) -> ClockLabel:
        clock = ClockLabel(self._view)
        self._place_on(element_id, clock)
        return clock

    def place_all(self) -> None:
        """Move every overlay onto its SVG element."""
        for widget, element_id in self._slot_of_widget.items():
            widget.setGeometry(self._view.element_rect(element_id).toRect())

    def _place_on(self, element_id, widget):
        self._slot_of_widget[widget] = element_id
        self.place_all()
        widget.show()


def value_axis(plot: PyDMTimePlot):
    """The y-axis of a plot made by `Overlays.add_plot`."""
    return plot.plotItem.axes[PLOT_AXIS_NAME]["item"]


def _fix_y_range(axis, y_range, is_log):
    """Stop the axis from following the data and show `y_range` (lowest, highest) instead."""
    lowest, highest = y_range
    if is_log:
        # A logarithmic axis counts in powers of ten
        lowest, highest = math.log10(lowest), math.log10(highest)
    axis.auto_range = False
    axis.linkedView().setYRange(lowest, highest, padding=0)


def _foreground_on(background):
    """A color for lines and text that is readable on `background`."""
    if background.lightness() <= DARK_BACKGROUND_MAX_LIGHTNESS:
        return QColor(LIGHT_FOREGROUND)
    return QColor(DARK_FOREGROUND)


def _apply_format(label, value_format):
    label.displayFormat = DISPLAY_FORMATS[value_format.display_format]
    if value_format.precision is not None:
        label.precisionFromPV = False
        label.precision = value_format.precision
