"""Resolve bundled/relative resources, both in dev and inside a PyInstaller build."""
import sys
from pathlib import Path


def _roots():
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)  # next to the .exe (user can override files here)
        mp = getattr(sys, "_MEIPASS", None)
        if mp:
            roots.append(Path(mp))  # bundled data (_internal folder)
    else:
        roots.append(Path(__file__).resolve().parent)
    return roots


def resolve(rel: str) -> Path:
    for root in _roots():
        p = root / rel
        if p.exists():
            return p
    return _roots()[0] / rel
