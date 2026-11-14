"""Export the images of the panel from the drawing MAXI_synoptic_v2.svg.

    python tools/export_assets.py [--out DIR]

Run it after every edit of the drawing, and commit the result. It writes into
src/maxi_synoptic/resources/assets/ (or DIR):

  background.svg      everything drawn below the PyDM shapes of the differential pump stage, the
                      chamber and the detector, and the panels
  foreground.svg      everything drawn above them: beam path and arrow, diode, names, magnets

The script is a development tool; nothing in it runs with the panel.
"""

from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

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

# The hardware layer up to DIFFPUMP is background; from BEAM_axis on, it is drawn above the
# differential pump stage, the chamber and the detector, which are PyDM shapes between the two images.
FIRST_COVERED_HARDWARE = "DIFFPUMP"
FIRST_FOREGROUND_HARDWARE = "BEAM_axis"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the panel's images from the drawing")
    parser.add_argument("--out", type=Path, default=ASSETS_DIR, help="output directory")
    args = parser.parse_args()
    export(DRAWING, args.out)


def export(drawing: Path, out_dir: Path) -> None:
    """Write the background and foreground images of the drawing into `out_dir`."""
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)
    root = ET.parse(drawing).getroot()
    out_dir.mkdir(parents=True, exist_ok=True)
    background, foreground = split_layers(root)
    write_svg(root, background, CANVAS, out_dir / "background.svg")
    write_svg(root, foreground, CANVAS, out_dir / "foreground.svg")


def split_layers(root: ET.Element) -> tuple[list[ET.Element], list[ET.Element]]:
    """The elements below the chamber and detector shapes, and those above them."""
    hardware = layer(root, "layer_hardware")
    ids = [element.get("id") for element in hardware]
    below = hardware_part(hardware, 0, ids.index(FIRST_COVERED_HARDWARE))
    above = hardware_part(hardware, ids.index(FIRST_FOREGROUND_HARDWARE), len(ids))
    background = [layer(root, "layer_background"), below, layer(root, "layer_panels")]
    foreground = [above, layer(root, "layer_magnets")]
    return background, foreground


def hardware_part(hardware: ET.Element, start: int, end: int) -> ET.Element:
    part = copy.deepcopy(hardware)
    for index, child in reversed(list(enumerate(part))):
        if not start <= index < end:
            part.remove(child)
    return part


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


def layer(root: ET.Element, layer_id: str) -> ET.Element:
    return next(child for child in root if child.get("id") == layer_id)


def svg_tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


if __name__ == "__main__":
    main()
