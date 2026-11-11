from pathlib import Path

import numpy as np
import pytest
from qtpy.QtCore import QRectF
from qtpy.QtGui import QColor, QImage

from synoptic.svg_view import SvgDom, SvgView

FIXTURE = Path(__file__).parent / "fixture.svg"
GREEN = "#73d216"
GRAY = "#bfbfbf"
BACKGROUND = "#2e3436"
PURPLE_MARGIN = 20


@pytest.fixture
def dom():
    return SvgDom.from_file(FIXTURE)


@pytest.fixture
def view(qtbot, dom):
    view = SvgView(dom)
    qtbot.addWidget(view)
    view.resize(1920, 1080)
    view.show()
    qtbot.waitExposed(view)
    return view


def grab(view):
    return view.grab().toImage().convertToFormat(QImage.Format_ARGB32)


def color_at(image, x, y):
    return QColor(image.pixel(round(x), round(y))).name()


def purple_pixels(image, rect):
    """Return the (x, y) of all pixels in `rect` that show hatch lines.

    Antialiased lines mix with the fill, so every clearly purple pixel counts: more red and blue than green.
    """
    bits = image.constBits()
    bits.setsize(image.byteCount())
    pixels = np.frombuffer(bits, np.uint8).reshape(image.height(), image.width(), 4).astype(int)
    blue, green, red = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    is_purple = (red > green + PURPLE_MARGIN) & (blue > green + PURPLE_MARGIN)
    rect = rect & image.rect()
    rows, columns = np.nonzero(is_purple[rect.top() : rect.bottom() + 1, rect.left() : rect.right() + 1])
    return [(int(x) + rect.left(), int(y) + rect.top()) for x, y in zip(columns, rows)]


# --- DOM ---


def test_ids(dom):
    assert {"BACKGROUND", "CIRCLE", "SLOT_value", "inner"} <= dom.ids()


def test_round_trip_keeps_inkscape_attributes(dom):
    text = dom.to_bytes().decode()
    assert 'inkscape:label="circle"' in text
    assert 'inkscape:groupmode="layer"' in text
    assert 'sodipodi:docname="fixture.svg"' in text
    assert "ns0:" not in text
    assert SvgDom.from_bytes(dom.to_bytes()).ids() == dom.ids()


def test_set_style_changes_only_one_entry(dom):
    assert dom.get_style("CIRCLE", "fill") == GREEN
    assert dom.set_style("CIRCLE", "fill", GRAY) is True
    assert dom.get_style("CIRCLE", "fill") == GRAY
    assert dom.get_style("CIRCLE", "stroke") == "#404040"
    assert dom.get_style("CIRCLE", "stroke-width") == "4"
    assert dom.get_style("COVER", "fill") == "#ffffff"
    assert dom.set_style("CIRCLE", "fill", GRAY) is False


def test_set_style_on_element_without_style(dom):
    assert dom.get_style("PLAIN", "display") is None
    dom.set_style("PLAIN", "display", "none")
    assert dom.get_style("PLAIN", "display") == "none"
    dom.set_style("PLAIN", "display", None)
    assert dom.get_style("PLAIN", "display") is None


# --- scaling and coordinates ---


def test_drawing_is_scaled_and_centered(view):
    view.resize(1000, 1000)
    assert view.scale() == pytest.approx(1000 / 1920)
    drawing = view.drawing_rect()
    assert drawing.getRect() == pytest.approx((0, 218.75, 1000, 562.5))
    image = grab(view)
    assert color_at(image, 500, 100) == BACKGROUND  # leftover area above the drawing
    assert color_at(image, 500, 900) == BACKGROUND


def test_drawing_is_not_distorted(view):
    view.resize(1000, 1000)
    circle = view.element_rect("CIRCLE")
    assert circle.width() == pytest.approx(circle.height())
    image = grab(view)
    assert color_at(image, circle.center().x() - 30, circle.center().y()) == GREEN


def test_bounds_follow_nested_transforms(view):
    # x = 10 + 1000 + 20, y = 20 + 100 + 30
    assert view.svg_rect("SLOT_value") == QRectF(1030, 150, 200, 40)
    assert view.element_rect("SLOT_value") == QRectF(1030, 150, 200, 40)
    assert view.svg_rect("SLOT_value", include_stroke=True) == QRectF(1029, 149, 202, 42)


def test_bounds_of_transformed_group(view):
    assert view.svg_rect("STATE_ON") == QRectF(1500, 800, 100, 100)


def test_bounds_in_resized_window(view):
    view.resize(1000, 1000)
    scale = 1000 / 1920
    rect = view.element_rect("SLOT_value")
    assert rect.x() == pytest.approx(1030 * scale)
    assert rect.y() == pytest.approx(218.75 + 150 * scale)
    assert rect.width() == pytest.approx(200 * scale)
    assert rect.height() == pytest.approx(40 * scale)
    image = grab(view)
    assert color_at(image, rect.center().x(), rect.center().y()) == "#ffffff"


def test_resize_emits_signal(qtbot, view):
    with qtbot.waitSignal(view.resized, timeout=1000):
        view.resize(800, 600)


# --- changing elements and repaint batching ---


def test_fill_and_visibility(view):
    view.set_fill("CIRCLE", GRAY)
    view.set_visible("STATE_ON", True)
    view.set_visible("STATE_OFF", False)
    view.flush()
    image = grab(view)
    assert color_at(image, 350, 500) == GRAY
    assert color_at(image, 1550, 850) == GREEN
    assert view.is_visible("STATE_ON")
    assert not view.is_visible("STATE_OFF")


def test_burst_of_changes_is_drawn_once(qtbot, view):
    renders_before = view.render_count
    for index in range(50):
        view.set_fill("CIRCLE", "#0000%02x" % index)
    view.set_fill("CIRCLE", GRAY)
    assert view.render_count == renders_before
    qtbot.wait(300)
    assert view.render_count == renders_before + 1
    assert color_at(grab(view), 350, 500) == GRAY


def test_unchanged_value_does_not_repaint(qtbot, view):
    renders_before = view.render_count
    view.set_fill("CIRCLE", GREEN)
    view.set_hatched("CIRCLE", False)
    qtbot.wait(200)
    assert view.render_count == renders_before


# --- hatching ---


def hatched_view(view, element_id):
    view.set_fill(element_id, GRAY)
    view.set_hatched(element_id, True)
    view.flush()
    return grab(view)


def test_hatching_stays_inside_the_circle(view):
    image = hatched_view(view, "CIRCLE")
    bounds = view.element_rect("CIRCLE", include_stroke=True).toAlignedRect()
    purple = purple_pixels(image, bounds.adjusted(-20, -20, 20, 20))
    assert len(purple) > 500

    # the fill ends at r=98, where the 4 units wide stroke starts
    center_x, center_y, fill_radius = 400, 500, 98
    for x, y in purple:
        assert (x - center_x) ** 2 + (y - center_y) ** 2 <= (fill_radius + 1) ** 2

    gray_pixels = [1 for x in range(320, 380) if color_at(image, x, 520) == GRAY]
    assert len(gray_pixels) > 20


def test_hatching_is_not_drawn_on_elements_above(view):
    image = hatched_view(view, "CIRCLE")
    cover = view.element_rect("COVER").toAlignedRect()
    assert purple_pixels(image, cover.adjusted(1, 1, -1, -1)) == []


def test_hatching_follows_transforms(view):
    image = hatched_view(view, "MOVED_CIRCLE")
    # cx = 100 + 1000 + 20, cy = 400 + 100 + 30
    purple = purple_pixels(image, view.rect())
    assert len(purple) > 100
    for x, y in purple:
        assert (x - 1120) ** 2 + (y - 530) ** 2 <= 51**2


def test_hatching_follows_resize(view):
    hatched_view(view, "MOVED_CIRCLE")
    view.resize(960, 540)
    purple = purple_pixels(grab(view), view.rect())
    assert len(purple) > 25
    for x, y in purple:
        assert (x - 560) ** 2 + (y - 265) ** 2 <= 26**2


def test_hatching_is_removed(view):
    hatched_view(view, "CIRCLE")
    view.set_hatched("CIRCLE", False)
    view.set_fill("CIRCLE", GREEN)
    view.flush()
    assert purple_pixels(grab(view), view.rect()) == []
    assert view.fill("CIRCLE") == GREEN


def test_hatching_keeps_the_fill(view):
    hatched_view(view, "CIRCLE")
    assert view.fill("CIRCLE") == GRAY
