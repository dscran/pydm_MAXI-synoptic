"""The Designer file matches the drawing, the exported assets and the style sheet."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from qtpy.QtCore import QRectF
from qtpy.QtGui import QColor
from qtpy.QtSvg import QSvgRenderer

from maxi_synoptic.cli import RESOURCES_DIR, STYLE_SHEET, UI_FILE

DRAWING = RESOURCES_DIR / "MAXI_synoptic_v2.svg"
SYMBOL_CROPS = RESOURCES_DIR / "assets" / "symbols.json"
MAX_OFFSET = 1  # pixels

GREEN, YELLOW, BLUE, GRAY = "#4fae7b", "#d6a544", "#4b8fc4", "#6b7480"


@pytest.fixture(scope="module")
def ui_widgets():
    """Every widget of the .ui by name, as its XML element."""
    root = ET.parse(UI_FILE).getroot()
    return {widget.get("name"): widget for widget in root.iter("widget")}


@pytest.fixture(scope="module")
def drawing(qapp):
    return QSvgRenderer(str(DRAWING))


@pytest.fixture(scope="module")
def drawing_elements():
    root = ET.parse(DRAWING).getroot()
    return {element.get("id"): element for element in root.iter() if element.get("id")}


def geometry(widget):
    rect = widget.find("property[@name='geometry']/rect")
    return tuple(int(rect.find(key).text) for key in ("x", "y", "width", "height"))


def string_property(widget, name):
    return widget.find(f"property[@name='{name}']/string").text


def number_property(widget, name):
    return float(widget.find(f"property[@name='{name}']/double").text)


def color_property(widget, name):
    color = widget.find(f"property[@name='{name}']/color")
    return QColor(*(int(color.find(key).text) for key in ("red", "green", "blue"))).name()


def widgets_of(ui_widgets, class_name):
    return [widget for widget in ui_widgets.values() if widget.get("class") == class_name]


def slot_rect(drawing, element):
    """The rectangle of a slot element in panel coordinates, without its stroke."""
    rect = QRectF(*(float(element.get(key)) for key in ("x", "y", "width", "height")))
    return drawing.transformForElement(element.get("id")).mapRect(rect)


def style_of(element):
    declarations = (part.split(":", 1) for part in element.get("style").split(";") if part)
    return {key.strip(): value.strip() for key, value in declarations}


def assert_close(actual, expected):
    assert all(abs(a - e) <= MAX_OFFSET for a, e in zip(actual, expected)), f"{actual} != {expected}"


def test_labels_and_plots_cover_their_slots(ui_widgets, drawing, drawing_elements):
    widgets = widgets_of(ui_widgets, "PyDMLabel") + widgets_of(ui_widgets, "PyDMTimePlot")
    assert len(widgets) == 23
    for widget in widgets:
        rect = slot_rect(drawing, drawing_elements[widget.get("name")])
        assert_close(geometry(widget), (rect.x(), rect.y(), rect.width(), rect.height()))


def test_every_value_slot_has_a_label(ui_widgets, drawing_elements):
    slots = {element_id for element_id in drawing_elements if element_id.endswith("_value")}
    labels = {widget.get("name") for widget in widgets_of(ui_widgets, "PyDMLabel")}
    assert labels == slots - {"DATETIME_value"}


def test_symbols_stack_like_the_drawing(ui_widgets, drawing_elements):
    """The beam is drawn over the valve and the shutter, as in the drawing."""
    drawing_order = list(drawing_elements)

    def first_drawing(symbol):
        image_files = json.loads(string_property(symbol, "imageFiles")).values()
        state_ids = [Path(file).stem for file in image_files if Path(file).stem in drawing_elements]
        return min(drawing_order.index(state_id) for state_id in state_ids)

    symbols = widgets_of(ui_widgets, "PyDMSymbol")
    assert symbols == sorted(symbols, key=first_drawing)


def test_symbols_match_their_crops(ui_widgets):
    crops = json.loads(SYMBOL_CROPS.read_text())
    symbols = widgets_of(ui_widgets, "PyDMSymbol")
    assert {symbol.get("name") for symbol in symbols} == set(crops)
    for symbol in symbols:
        crop = crops[symbol.get("name")]
        assert geometry(symbol) == (crop["x"], crop["y"], crop["width"], crop["height"])


def drawn_shape(widget):
    """The box that PyDM draws a circle or rectangle in: the widget, less the pen width on each side."""
    x, y, width, height = geometry(widget)
    pen = number_property(widget, "penWidth")
    return x + pen, y + pen, width - 2 * pen, height - 2 * pen


def assert_same_outline(widget, element):
    style = style_of(element)
    # PyDM draws no border without a pen style, whatever the pen colour and width
    assert widget.find("property[@name='penStyle']/enum").text == "Qt::SolidLine"
    assert color_property(widget, "penColor") == style["stroke"]
    assert number_property(widget, "penWidth") == float(style["stroke-width"])


def test_chamber_shape_covers_maxichamber(ui_widgets, drawing_elements):
    chamber = drawing_elements["MAXICHAMBER"]
    center_x, center_y, radius = (float(chamber.get(key)) for key in ("cx", "cy", "r"))
    expected = (center_x - radius, center_y - radius, 2 * radius, 2 * radius)
    assert drawn_shape(ui_widgets["chamber"]) == expected
    assert_same_outline(ui_widgets["chamber"], chamber)


def test_detector_shape_covers_detector(ui_widgets, drawing_elements):
    detector = drawing_elements["DETECTOR"]
    assert detector.get("rx") is None, "PyDM's rectangle has square corners"
    expected = tuple(float(detector.get(key)) for key in ("x", "y", "width", "height"))
    assert drawn_shape(ui_widgets["detector"]) == expected
    assert_same_outline(ui_widgets["detector"], detector)


def style_sheet_image_files(symbol_name, severity):
    """The imageFiles that the style sheet sets on a symbol at an alarm severity."""
    selector = re.escape(f'PyDMSymbol#{symbol_name}[alarmSeverity="{severity}"]')
    rule = re.search(selector + r"[^{]*\{\s*qproperty-imageFiles:\s*'([^']*)'", STYLE_SHEET.read_text())
    assert rule, f"no imageFiles for {symbol_name} at severity {severity}"
    return json.loads(rule.group(1))


@pytest.mark.parametrize("severity", [0, 1, 2])
def test_style_sheet_repeats_the_normal_images(ui_widgets, severity):
    for symbol in widgets_of(ui_widgets, "PyDMSymbol"):
        normal = json.loads(string_property(symbol, "imageFiles"))
        assert style_sheet_image_files(symbol.get("name"), severity) == normal


@pytest.mark.parametrize("severity", [3, 4])
def test_style_sheet_has_unknown_images(ui_widgets, severity):
    for symbol in widgets_of(ui_widgets, "PyDMSymbol"):
        unknown = style_sheet_image_files(symbol.get("name"), severity)
        assert set(unknown) == set(json.loads(string_property(symbol, "imageFiles")))
        assert len(set(unknown.values())) == 1


def rule_color(widget, value):
    """The colour that the widget's only rule gives for a channel value, evaluated as PyDM does."""
    (rule,) = json.loads(string_property(widget, "rules"))
    assert rule["property"] == "Set Brush Color"
    assert rule["channels"][0]["channel"] == string_property(widget, "channel")
    return QColor(eval(rule["expression"], {"ch": [value], "QColor": QColor})).name()


@pytest.mark.parametrize(
    ("pressure", "color"),
    [
        (3e-7, GREEN),
        (5e-6, GREEN),
        (5.1e-6, YELLOW),
        (1e-3, YELLOW),
        (700, YELLOW),
        (700.1, GRAY),
        (1013, GRAY),
    ],
)
def test_chamber_colors(ui_widgets, pressure, color):
    assert rule_color(ui_widgets["chamber"], pressure) == color


@pytest.mark.parametrize(("temperature", "color"), [(-40, BLUE), (15, BLUE), (15.1, GRAY), (22, GRAY)])
def test_detector_colors(ui_widgets, temperature, color):
    assert rule_color(ui_widgets["detector"], temperature) == color
