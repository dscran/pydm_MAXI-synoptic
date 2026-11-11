import os
import sys
from pathlib import Path

# Qt must not need a screen, and this has to be set before Qt is imported
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))
