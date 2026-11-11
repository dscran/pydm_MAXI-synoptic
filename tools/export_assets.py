"""Export the images of the panel from the drawing MAXI_synoptic_v2.svg.

    python tools/export_assets.py [--out DIR]

Run it after every edit of the drawing, and commit the result. It writes into
src/maxi_synoptic/resources/assets/ (or DIR):

  background.svg      everything drawn below the chamber and the detector, and the panels
  foreground.svg      everything drawn above them: beam axis, diode, names, magnets, beam entry
  <STATE_ID>.svg      one file per state drawing, cropped to the bounds of its symbol
  <symbol>_none.svg   an empty image with the same crop, for a symbol value that shows nothing
  symbols.json        the crop of each symbol, which is the geometry of its PyDMSymbol in the .ui

The script is a development tool; nothing in it runs with the panel.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# No window is shown, so the export runs without a screen, whatever platform the session sets.
# Set before Qt is imported.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from qtpy.QtCore import QByteArray, QRectF  # noqa: E402
from qtpy.QtSvg import QSvgRenderer  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "src" / "maxi_synoptic" / "resources"
DRAWING = RESOURCES_DIR / "MAXI_synoptic_v2.svg"
ASSETS_DIR = RESOURCES_DIR / "assets"

SVG_NS = "http://www.w3.org/2000/svg"
NAMESPACES = {
    "": SVG_NS,
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
}
CANVAS = (0, 0, 1920, 1080)

# The state drawings of each PyDMSymbol of the panel
SYMBOLS = {
    "beam_valve": ("BEAM_VALVE_CLOSED", "BEAM_VALVE_OPEN"),
    "beam_shutter": ("BEAM_SHUTTER_OPEN", "BEAM_SHUTTER_CLOSED", "BEAM_SHUTTER_UNKNOWN"),
    "valve": ("VALVE_CLOSED", "VALVE_OPEN", "VALVE_UNKNOWN"),
    "shutter": ("SHUTTER_CLOSED", "SHUTTER_OPEN", "SHUTTER_UNKNOWN"),
}
ALL_STATE_IDS = {state_id for state_ids in SYMBOLS.values() for state_id in state_ids}
# The hardware layer up to MAXICHAMBER is background; from BEAM_axis on, it is drawn above the
# chamber and the detector, which are PyDM shapes between the two images.
FIRST_COVERED_HARDWARE = "MAXICHAMBER"
FIRST_FOREGROUND_HARDWARE = "BEAM_axis"
# Room around the drawn bounds for antialiasing
CROP_PADDING = 4
# Qt gives <text> no bounds. The state words sit up to TEXT_TOP_MARGIN above the drawing they belong
# to, and stick out by up to TEXT_SIDE_MARGIN on each side ("CLOSED" is wider than the shutter).
TEXT_TOP_MARGIN = 36
TEXT_SIDE_MARGIN = 24


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the panel's images from the drawing")
    parser.add_argument("--out", type=Path, default=ASSETS_DIR, help="output directory")
    args = parser.parse_args()
    _app = QApplication.instance() or QApplication(sys.argv[:1])  # QSvgRenderer needs it
    export(DRAWING, args.out)


def export(drawing: Path, out_dir: Path) -> None:
    """Write all images and symbols.json of the drawing into `out_dir`."""
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)
    root = ET.parse(drawing).getroot()
    out_dir.mkdir(parents=True, exist_ok=True)
    background, foreground = split_layers(root)
    write_svg(root, background, CANVAS, out_dir / "background.svg")
    write_svg(root, foreground, CANVAS, out_dir / "foreground.svg")
    crops = {name: export_symbol(root, name, state_ids, out_dir) for name, state_ids in SYMBOLS.items()}
    (out_dir / "symbols.json").write_text(json.dumps(crops, indent=2) + "\n")


def split_layers(root: ET.Element) -> tuple[list[ET.Element], list[ET.Element]]:
    """The elements below the chamber and detector shapes, and those above them."""
    hardware = layer(root, "layer_hardware")
    ids = [element.get("id") for element in hardware]
    below = hardware_part(hardware, 0, ids.index(FIRST_COVERED_HARDWARE))
    above = hardware_part(hardware, ids.index(FIRST_FOREGROUND_HARDWARE), len(ids))
    beam_entry = element_by_id(root, "BEAM_entry")
    background = [layer(root, "layer_background"), below, layer(root, "layer_panels")]
    foreground = [above, layer(root, "layer_magnets"), beam_entry]
    return background, foreground


def hardware_part(hardware: ET.Element, start: int, end: int) -> ET.Element:
    part = copy.deepcopy(hardware)
    for index, child in reversed(list(enumerate(part))):
        if not start <= index < end:
            part.remove(child)
    return part


def export_symbol(root: ET.Element, name: str, state_ids: tuple[str, ...], out_dir: Path) -> dict:
    """Write the state drawings of a symbol and its empty image, all with one crop; return the crop."""
    states = {state_id: state_drawing(root, state_id) for state_id in state_ids}
    crop = crop_of(root, list(states.values()))
    for state_id, element in states.items():
        write_svg(root, [element], crop, out_dir / f"{state_id}.svg")
    write_svg(root, [], crop, out_dir / f"{name}_none.svg")
    x, y, width, height = crop
    return {"x": x, "y": y, "width": width, "height": height}


def state_drawing(root: ET.Element, state_id: str) -> ET.Element:
    """A visible copy of a state drawing, without the drawings nested in it that have their own symbol."""
    element = copy.deepcopy(element_by_id(root, state_id))
    for nested in list(element):
        if nested.get("id") in ALL_STATE_IDS:
            element.remove(nested)
    for descendant in element.iter():
        strip_display_none(descendant)
    return element


def crop_of(root: ET.Element, elements: list[ET.Element]) -> tuple[int, int, int, int]:
    """The whole-pixel box (x, y, width, height) around the drawn elements, with room for their words."""
    renderer = QSvgRenderer(QByteArray(ET.tostring(svg_document(root, elements, CANVAS))))
    drawn = QRectF()
    for element in elements:
        for descendant in element.iter():
            if descendant.get("id"):
                drawn = drawn.united(renderer.boundsOnElement(descendant.get("id")))
    if drawn.isEmpty():
        raise ValueError(f"nothing drawn in {[element.get('id') for element in elements]}")
    if contains_text(elements):
        drawn.adjust(-TEXT_SIDE_MARGIN, -TEXT_TOP_MARGIN, TEXT_SIDE_MARGIN, 0)
    left = math.floor(drawn.left() - CROP_PADDING)
    top = math.floor(drawn.top() - CROP_PADDING)
    right = math.ceil(drawn.right() + CROP_PADDING)
    bottom = math.ceil(drawn.bottom() + CROP_PADDING)
    return left, top, right - left, bottom - top


def contains_text(elements: list[ET.Element]) -> bool:
    texts = (text for element in elements for text in element.iter(svg_tag("text")))
    return next(texts, None) is not None


def write_svg(root: ET.Element, children: list[ET.Element], view_box: tuple, path: Path) -> None:
    tree = ET.ElementTree(svg_document(root, children, view_box))
    ET.indent(tree)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def svg_document(root: ET.Element, children: list[ET.Element], view_box: tuple) -> ET.Element:
    """A new SVG of the size of `view_box`, with the defs of the drawing and copies of `children`."""
    x, y, width, height = view_box
    document = ET.Element(root.tag, {"version": root.get("version", "1.1")})
    document.set("viewBox", f"{x} {y} {width} {height}")
    document.set("width", str(width))
    document.set("height", str(height))
    defs = root.find(svg_tag("defs"))
    if defs is not None:
        document.append(copy.deepcopy(defs))
    document.extend(copy.deepcopy(child) for child in children)
    return document


def strip_display_none(element: ET.Element) -> None:
    style = element.get("style")
    if style is None:
        return
    declarations = [part for part in style.split(";") if part.strip() != "display:none"]
    element.set("style", ";".join(declarations))


def layer(root: ET.Element, layer_id: str) -> ET.Element:
    return next(child for child in root if child.get("id") == layer_id)


def element_by_id(root: ET.Element, element_id: str) -> ET.Element:
    found = root.find(f".//*[@id='{element_id}']")
    if found is None:
        raise KeyError(f"the drawing has no element with id {element_id!r}")
    return found


def svg_tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


if __name__ == "__main__":
    main()
