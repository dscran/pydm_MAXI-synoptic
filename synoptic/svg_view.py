"""An SVG kept in memory, and a widget that draws it and maps its elements to widget coordinates."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from pathlib import Path

import numpy as np
from qtpy.QtCore import QByteArray, QPoint, QRectF, QSize, Qt, QTimer, Signal
from qtpy.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import QWidget

NAMESPACES = {
    "": "http://www.w3.org/2000/svg",
    "svg": "http://www.w3.org/2000/svg",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "xlink": "http://www.w3.org/1999/xlink",
}

BACKGROUND_ID = "BACKGROUND"
FALLBACK_BACKGROUND = "#000000"
REPAINT_DELAY_MS = 100

HATCH_COLOR = "#c79bea"
HATCH_LINE_WIDTH = 3
HATCH_SPACING = 16

VISIBLE = "inline"
HIDDEN = "none"


class SvgDom:
    """The SVG document. It can change the `style` entries of elements, addressed by their id."""

    def __init__(self, root: ElementTree.Element):
        self._root = root
        self._elements = {element.get("id"): element for element in root.iter() if element.get("id")}

    @classmethod
    def from_file(cls, path: str | Path) -> SvgDom:
        return cls.from_bytes(Path(path).read_bytes())

    @classmethod
    def from_bytes(cls, data: bytes) -> SvgDom:
        # Without registered prefixes, ElementTree would write ns0, ns1, ... instead of inkscape, sodipodi
        for prefix, uri in NAMESPACES.items():
            ElementTree.register_namespace(prefix, uri)
        return cls(ElementTree.fromstring(data))

    def ids(self) -> set[str]:
        return set(self._elements)

    def get_style(self, element_id: str, key: str) -> str | None:
        """Return one entry of the element's `style` attribute, or None if it is not set."""
        return self._style(element_id).get(key)

    def set_style(self, element_id: str, key: str, value: str | None) -> bool:
        """Set one entry of the element's `style` attribute, or remove it with None.

        Returns True if this changed the document.
        """
        style = self._style(element_id)
        if style.get(key) == value:
            return False
        if value is None:
            del style[key]
        else:
            style[key] = value
        style_text = ";".join(f"{name}:{entry}" for name, entry in style.items())
        self._elements[element_id].set("style", style_text)
        return True

    def to_bytes(self) -> bytes:
        return ElementTree.tostring(self._root, encoding="utf-8", xml_declaration=True)

    def _style(self, element_id):
        style = {}
        for entry in self._elements[element_id].get("style", "").split(";"):
            name, separator, value = entry.partition(":")
            if separator:
                style[name.strip()] = value.strip()
        return style


class SvgView(QWidget):
    """Draws an SvgDom scaled to fit and centered, and tells where its elements are on screen.

    Changes to elements are collected and drawn together, at most once per REPAINT_DELAY_MS.
    """

    resized = Signal()

    def __init__(self, dom: SvgDom, parent: QWidget | None = None):
        super().__init__(parent)
        self._dom = dom
        self._renderer = QSvgRenderer(self)
        self._hatched = set()
        self._drawn_hatched = set()
        self._hatch_images = {}
        self._hatch_brush = QBrush(_hatch_tile())
        self._background = QColor(dom_background(dom))
        self.render_count = 0

        self._repaint_timer = QTimer(self)
        self._repaint_timer.setSingleShot(True)
        self._repaint_timer.setInterval(REPAINT_DELAY_MS)
        self._repaint_timer.timeout.connect(self.flush)
        self.flush()

    # --- geometry ---

    def sizeHint(self) -> QSize:
        return self._renderer.viewBoxF().size().toSize()

    def scale(self) -> float:
        """Widget pixels per SVG unit."""
        view_box = self._renderer.viewBoxF()
        return min(self.width() / view_box.width(), self.height() / view_box.height())

    def drawing_rect(self) -> QRectF:
        """The area of the widget covered by the SVG."""
        view_box = self._renderer.viewBoxF()
        width = view_box.width() * self.scale()
        height = view_box.height() * self.scale()
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def svg_rect(self, element_id: str, include_stroke: bool = False) -> QRectF:
        """The bounds of an element in SVG units, after the transforms of the element and its ancestors."""
        bounds = self._renderer.boundsOnElement(element_id)
        if not include_stroke:
            # Qt's bounds include the stroke, which lies half outside of the element's geometry
            margin = self._stroke_width(element_id) / 2
            bounds = bounds.adjusted(margin, margin, -margin, -margin)
        return self._renderer.transformForElement(element_id).mapRect(bounds)

    def element_rect(self, element_id: str, include_stroke: bool = False) -> QRectF:
        """The bounds of an element in widget coordinates."""
        return self._to_widget(self.svg_rect(element_id, include_stroke))

    def _to_widget(self, svg_rect):
        view_box = self._renderer.viewBoxF()
        drawing = self.drawing_rect()
        scale = self.scale()
        return QRectF(
            drawing.x() + (svg_rect.x() - view_box.x()) * scale,
            drawing.y() + (svg_rect.y() - view_box.y()) * scale,
            svg_rect.width() * scale,
            svg_rect.height() * scale,
        )

    def _stroke_width(self, element_id):
        if self._dom.get_style(element_id, "stroke") in (None, "none"):
            return 0.0
        try:
            return float(self._dom.get_style(element_id, "stroke-width") or 1)
        except ValueError:
            return 0.0

    # --- changing elements ---

    def set_fill(self, element_id: str, color: str) -> None:
        self._change_style(element_id, "fill", color)

    def set_visible(self, element_id: str, is_visible: bool) -> None:
        self._change_style(element_id, "display", VISIBLE if is_visible else HIDDEN)

    def is_visible(self, element_id: str) -> bool:
        return self._dom.get_style(element_id, "display") != HIDDEN

    def fill(self, element_id: str) -> str | None:
        return self._dom.get_style(element_id, "fill")

    def set_hatched(self, element_id: str, is_hatched: bool) -> None:
        """Draw hatching over the visible fill of an element, or remove it."""
        if is_hatched == (element_id in self._hatched):
            return
        if is_hatched:
            self._hatched.add(element_id)
        else:
            self._hatched.discard(element_id)
        self._schedule_repaint()

    def hatched(self) -> set[str]:
        return set(self._hatched)

    def flush(self) -> None:
        """Draw all pending changes now, instead of waiting for the repaint timer."""
        self._repaint_timer.stop()
        self._renderer.load(QByteArray(self._dom.to_bytes()))
        self._drawn_hatched = set(self._hatched)
        self._hatch_images.clear()
        self.render_count += 1
        self.update()

    def _change_style(self, element_id, key, value):
        if self._dom.set_style(element_id, key, value):
            self._schedule_repaint()

    def _schedule_repaint(self):
        if not self._repaint_timer.isActive():
            self._repaint_timer.start()

    # --- painting ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._hatch_images.clear()
        self.resized.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._background)
        self._renderer.render(painter, self.drawing_rect())
        for element_id in sorted(self._drawn_hatched):
            self._paint_hatching(painter, element_id)
        painter.end()

    def _paint_hatching(self, painter, element_id):
        if element_id not in self._hatch_images:
            self._hatch_images[element_id] = self._build_hatching(element_id)
        area, image = self._hatch_images[element_id]
        if image is not None:
            painter.drawImage(area.topLeft(), image)

    def _build_hatching(self, element_id):
        """Return the widget area of an element and an image with hatch lines on its visible fill."""
        area = self.element_rect(element_id, include_stroke=True).toAlignedRect() & self.rect()
        if area.isEmpty():
            return area, None
        coverage = self._fill_coverage(element_id, area)
        shape = QImage(coverage.tobytes(), area.width(), area.height(), area.width(), QImage.Format_Alpha8)

        image = QImage(area.size(), QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        # Anchor the pattern to the widget, so that the lines of neighbouring elements line up
        painter.setBrushOrigin(-area.topLeft())
        painter.fillRect(image.rect(), self._hatch_brush)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawImage(QPoint(0, 0), shape)
        painter.end()
        return area, image

    def _fill_coverage(self, element_id, area):
        """Return how much of each pixel in `area` shows the fill of the element (0-255).

        The SVG is drawn once with a black and once with a white fill. Only pixels that show the fill
        differ, so the stroke and everything drawn on top of the element are left out.
        """
        original_fill = self._dom.get_style(element_id, "fill")
        black = self._render_with_fill(element_id, "#000000", area)
        white = self._render_with_fill(element_id, "#ffffff", area)
        self._dom.set_style(element_id, "fill", original_fill)
        return (white.astype(np.int16) - black).clip(0, 255).astype(np.uint8)

    def _render_with_fill(self, element_id, fill, area):
        """Draw the part of the SVG inside `area` and return one color channel as an array."""
        self._dom.set_style(element_id, "fill", fill)
        renderer = QSvgRenderer(QByteArray(self._dom.to_bytes()))
        image = QImage(area.size(), QImage.Format_RGB32)
        image.fill(Qt.gray)
        painter = QPainter(image)
        painter.translate(-area.topLeft())
        renderer.render(painter, self.drawing_rect())
        painter.end()
        return _blue_channel(image)


def dom_background(dom: SvgDom) -> str:
    """The fill of the SVG's background element, used for the area around the drawing."""
    if BACKGROUND_ID not in dom.ids():
        return FALLBACK_BACKGROUND
    return dom.get_style(BACKGROUND_ID, "fill") or FALLBACK_BACKGROUND


def _blue_channel(image):
    bits = image.constBits()
    bits.setsize(image.byteCount())
    rows = np.frombuffer(bits, np.uint8).reshape(image.height(), image.bytesPerLine())
    pixels = rows[:, : image.width() * 4].reshape(image.height(), image.width(), 4)
    return pixels[:, :, 0].copy()


def _hatch_tile():
    """A tile with diagonal lines, like Qt.BDiagPattern but with a chosen line width."""
    tile = QPixmap(HATCH_SPACING, HATCH_SPACING)
    tile.fill(Qt.transparent)
    painter = QPainter(tile)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(HATCH_COLOR), HATCH_LINE_WIDTH))
    # The neighbouring lines fill in the corners, so that the tiles join without gaps
    for offset in (-HATCH_SPACING, 0, HATCH_SPACING):
        painter.drawLine(offset, HATCH_SPACING, offset + HATCH_SPACING, 0)
    painter.end()
    return tile
