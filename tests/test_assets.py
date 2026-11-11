"""The committed images of the panel are up to date with the drawing."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
EXPORT_SCRIPT = REPO_DIR / "tools" / "export_assets.py"
COMMITTED_DIR = REPO_DIR / "src" / "maxi_synoptic" / "resources" / "assets"


@pytest.fixture(scope="module")
def exported_dir(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("assets")
    subprocess.run([sys.executable, str(EXPORT_SCRIPT), "--out", str(out_dir)], check=True, timeout=60)
    return out_dir


def file_names(directory):
    return sorted(path.name for path in directory.iterdir())


def test_same_files(exported_dir):
    assert file_names(exported_dir) == file_names(COMMITTED_DIR)


@pytest.mark.parametrize("file_name", file_names(COMMITTED_DIR))
def test_file_is_up_to_date(exported_dir, file_name):
    exported = (exported_dir / file_name).read_text()
    committed = (COMMITTED_DIR / file_name).read_text()
    assert exported == committed, f"{file_name} is out of date: run python tools/export_assets.py"
