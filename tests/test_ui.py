"""The Designer files match the drawing, the design of the valve and the shutter, and the style sheet."""

import json
import re
import xml.etree.ElementTree as ET

import pytest
from qtpy.QtCore import QRectF
from qtpy.QtGui import QColor
from qtpy.QtSvg import QSvgRenderer

from maxi_synoptic.cli import MACRO_PATTERN, RESOURCES_DIR, STYLE_SHEET, UI_FILE

DRAWING = RESOURCES_DIR / "MAXI_synoptic_v2.svg"
VALVE_UI = RESOURCES_DIR / "valve.ui"
SHUTTER_UI = RESOURCES_DIR / "shutter.ui"
MAX_OFFSET = 1  # pixels

GREEN, YELLOW, RED, BLUE, GRAY = "#4fae7b", "#d6a544", "#cf5b5b", "#4b8fc4", "#6b7480"
DARK, CLEAR, SILVER, AMBER = "#262b31", "clear", "#aab4bf", "#f0c75e"


def widgets_by_name(ui_file):
    """Every widget of a .ui file by name, as its XML element."""
    root = ET.parse(ui_file).getroot()
    return {widget.get("name"): widget for widget in root.iter("widget")}


@pytest.fixture(scope="module")
def ui_widgets():
    return widgets_by_name(UI_FILE)


@pytest.fixture(scope="module")
def valve_widgets():
    return widgets_by_name(VALVE_UI)


@pytest.fixture(scope="module")
def shutter_widgets():
    return widgets_by_name(SHUTTER_UI)


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


def test_diffpump_shape_covers_diffpump(ui_widgets, drawing_elements):
    diffpump = drawing_elements["DIFFPUMP"]
    expected = tuple(float(diffpump.get(key)) for key in ("x", "y", "width", "height"))
    # PyDM insets the drawing by the pen width, 2.5 px, so it can only come within half a pixel
    assert_close(drawn_shape(ui_widgets["diffpump"]), expected)
    assert_same_outline(ui_widgets["diffpump"], diffpump)


def test_diffpump_stacks_with_the_chamber_and_detector(ui_widgets):
    names = list(ui_widgets)
    assert names.index("detector") < names.index("diffpump") < names.index("foreground")


def rule_result(widget, value, property_name):
    """What the widget's only rule gives for a channel value, evaluated as PyDM does."""
    (rule,) = json.loads(string_property(widget, "rules"))
    assert rule["property"] == property_name
    assert rule["channels"][0]["channel"] == string_property(widget, "channel")
    return eval(rule["expression"], {"ch": [value], "QColor": QColor})


def rule_color(widget, value, property_name="Set Brush Color"):
    """The colour that the widget's only rule gives for a channel value, or "clear" if transparent."""
    color = QColor(rule_result(widget, value, property_name))
    if color.alpha() == 0:
        return CLEAR
    return color.name()


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


@pytest.mark.parametrize(
    ("pressure", "color"),
    [(8e-9, GREEN), (1e-7, GREEN), (5e-7, YELLOW), (1e-6, YELLOW), (1e-2, RED), (700, RED), (1013, GRAY)],
)
def test_diffpump_colors(ui_widgets, pressure, color):
    assert rule_color(ui_widgets["diffpump"], pressure) == color


# The valve: one look per value, from the table in the design of qt-drawn-valve-shutter
VALVE_GATES = ("valve_gate_top", "valve_gate_upper", "valve_gate_lower", "valve_gate_bottom")
VALVE_WORDS = ("valve_word_closed", "valve_word_open", "valve_word_moving")
# Body, gates, shown word, and whether the "?" of a value without a state is shown
VALVE_NO_STATE = (GRAY, (CLEAR, CLEAR, CLEAR, CLEAR), None, True)
VALVE_LOOKS = {
    0: (RED, (DARK, DARK, DARK, DARK), "valve_word_closed", False),
    1: (GREEN, (DARK, CLEAR, CLEAR, DARK), "valve_word_open", False),
    2: (YELLOW, (DARK, DARK, CLEAR, DARK), "valve_word_moving", False),
    3: VALVE_NO_STATE,
    5: VALVE_NO_STATE,
    -1: VALVE_NO_STATE,
}


@pytest.mark.parametrize("value", list(VALVE_LOOKS))
def test_valve_looks(valve_widgets, value):
    body, gates, word, question_mark = VALVE_LOOKS[value]
    assert rule_color(valve_widgets["valve_body"], value) == body
    assert tuple(rule_color(valve_widgets[name], value) for name in VALVE_GATES) == gates
    shown_words = [name for name in VALVE_WORDS if rule_result(valve_widgets[name], value, "Visible")]
    assert shown_words == ([word] if word else [])
    assert rule_result(valve_widgets["valve_out_of_range"], value, "Visible") == question_mark


def test_valve_question_marks_overlap(valve_widgets):
    """A value without a state looks like an unknown value: both "?" are at the same place."""
    assert geometry(valve_widgets["valve_out_of_range"]) == geometry(valve_widgets["valve_unknown"])


@pytest.mark.parametrize("ui_file", [VALVE_UI, SHUTTER_UI])
def test_device_display_uses_only_its_channel_macro(ui_file):
    assert set(MACRO_PATTERN.findall(ui_file.read_text())) == {"ch"}
    channels = [
        widget.find("property[@name='channel']/string") for widget in widgets_by_name(ui_file).values()
    ]
    assert {channel.text for channel in channels if channel is not None} == {"${ch}"}


def test_valve_words_keep_their_text(valve_widgets):
    for name in (*VALVE_WORDS, "valve_unknown", "valve_out_of_range"):
        widget = valve_widgets[name]
        assert widget.find("property[@name='displayLabelText']/bool").text == "true"
    texts = [string_property(valve_widgets[name], "text") for name in VALVE_WORDS]
    assert texts == ["CLOSED", "OPEN", "MOVING"]


def style_sheet_rules():
    """Each rule of the style sheet as (selectors, declarations), without comments."""
    text = re.sub(r"/\*.*?\*/", "", STYLE_SHEET.read_text(), flags=re.DOTALL)
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", text):
        yield [selector.strip() for selector in selectors.split(",")], body


def severity_of(selector):
    severity = re.search(r'\[alarmSeverity="(\d)"\]', selector)
    return int(severity.group(1)) if severity else None


@pytest.mark.parametrize("ui_file", [VALVE_UI, SHUTTER_UI])
def test_style_sheet_sets_no_brush_or_pen_for_known_values(ui_file):
    """Brushes and pens of a known value belong to the rules; the style sheet sets them only when unknown."""
    names = set(widgets_by_name(ui_file))
    severities = []
    for selectors, body in style_sheet_rules():
        if "qproperty-brush" not in body and "qproperty-pen" not in body:
            continue
        for selector in selectors:
            widget_name = re.search(r"#(\w+)", selector)
            if widget_name and widget_name.group(1) in names:
                severities.append(severity_of(selector))
    assert severities, f"the style sheet sets no unknown look for {ui_file.name}"
    assert set(severities) == {3, 4}


# The shutter: frame pen, blade fills from top to bottom, and the shown word
SHUTTER_BLADES = ("shutter_blade_top", "shutter_blade_mid", "shutter_blade_bottom")
SHUTTER_WORDS = ("shutter_word_open", "shutter_word_closed")
SHUTTER_LOOKS = {
    True: (AMBER, (SILVER, CLEAR, SILVER), "shutter_word_open"),
    False: (BLUE, (BLUE, BLUE, BLUE), "shutter_word_closed"),
}


@pytest.mark.parametrize("value", list(SHUTTER_LOOKS))
def test_shutter_looks(shutter_widgets, value):
    frame, blades, word = SHUTTER_LOOKS[value]
    assert rule_color(shutter_widgets["shutter_frame"], value, "Set Pen Color") == frame
    assert tuple(rule_color(shutter_widgets[name], value) for name in SHUTTER_BLADES) == blades
    shown_words = [name for name in SHUTTER_WORDS if rule_result(shutter_widgets[name], value, "Visible")]
    assert shown_words == [word]


def test_shutter_words_keep_their_text(shutter_widgets):
    for name in (*SHUTTER_WORDS, "shutter_unknown"):
        assert shutter_widgets[name].find("property[@name='displayLabelText']/bool").text == "true"
    assert [string_property(shutter_widgets[name], "text") for name in SHUTTER_WORDS] == ["OPEN", "CLOSED"]


@pytest.mark.parametrize(
    ("name", "ui_file", "signal", "expected_geometry"),
    [
        ("valve", VALVE_UI, "valve_state", (1310, 442, 196, 184)),
        ("shutter", SHUTTER_UI, "shutter_open", (1094, 432, 128, 214)),
    ],
)
def test_device_is_one_embedded_display(ui_widgets, name, ui_file, signal, expected_geometry):
    widget = ui_widgets[name]
    assert widget.get("class") == "PyDMEmbeddedDisplay"
    assert geometry(widget) == expected_geometry
    assert string_property(widget, "filename") == ui_file.name
    assert json.loads(string_property(widget, "macros")) == {"ch": f"${{{signal}}}"}
    assert widget.find("property[@name='frameShape']/enum").text == "QFrame::NoFrame"


def test_beam_path_is_drawn_over_the_devices(ui_widgets):
    """The foreground image, with the dashed beam path, is above the valve and the shutter."""
    names = list(ui_widgets)
    assert names.index("diffpump") < names.index("valve") < names.index("foreground")
    assert names.index("diffpump") < names.index("shutter") < names.index("foreground")
