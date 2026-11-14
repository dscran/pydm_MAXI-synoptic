import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
RESOURCE_FILES = [
    "maxi_synoptic.ui",
    "valve.ui",
    "shutter.ui",
    "maxi_synoptic.qss",
    "default.json",
    "sim.json",
    "assets/background.svg",
    "assets/foreground.svg",
]
DEPENDENCIES = {"pydm", "pytango"}


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    """A wheel built from the checkout."""
    out_dir = tmp_path_factory.mktemp("wheel")
    command = [sys.executable, "-m", "pip", "wheel", str(REPO_DIR), "--no-deps", "--no-build-isolation"]
    subprocess.run([*command, "--wheel-dir", str(out_dir)], check=True, capture_output=True, timeout=300)
    (wheel,) = out_dir.glob("maxi_synoptic-*.whl")
    return wheel


@pytest.fixture(scope="module")
def wheel_names(wheel):
    """Names of all files in the wheel."""
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


def wheel_metadata(wheel):
    with zipfile.ZipFile(wheel) as archive:
        (metadata,) = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        return archive.read(metadata).decode()


@pytest.mark.parametrize("file_name", RESOURCE_FILES)
def test_wheel_contains_resource(wheel_names, file_name):
    assert f"maxi_synoptic/resources/{file_name}" in wheel_names


def test_wheel_has_only_the_package_at_top_level(wheel_names):
    top_level = {name.split("/")[0] for name in wheel_names}
    dist_info = {name for name in top_level if name.endswith(".dist-info")}
    assert len(dist_info) == 1
    assert top_level - dist_info == {"maxi_synoptic"}


def test_wheel_has_every_exported_asset(wheel_names):
    committed = {path.name for path in (REPO_DIR / "src/maxi_synoptic/resources/assets").iterdir()}
    packaged = {Path(name).name for name in wheel_names if "/resources/assets/" in name}
    assert packaged == committed


def test_wheel_has_no_yaml(wheel_names):
    assert not [name for name in wheel_names if name.endswith((".yaml", ".yml"))]


def test_runtime_dependencies(wheel):
    requirements = {
        line.removeprefix("Requires-Dist: ").split(";")[0].strip()
        for line in wheel_metadata(wheel).splitlines()
        if line.startswith("Requires-Dist: ") and "extra ==" not in line
    }
    assert requirements == DEPENDENCIES
