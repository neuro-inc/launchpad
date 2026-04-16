"""Global test fixtures/helpers for the test suite.

This module provides a minimal stub for the optional native `magic`
library so tests that import application modules do not fail when
libmagic is not installed in the environment.
"""

import sys
from types import ModuleType


# Provide a minimal ModuleType stub for `magic` used by the application.
_magic_mod = ModuleType("magic")


class _DummyMagic:
    def __init__(self, mime: bool = True) -> None:  # pragma: no cover - trivial
        pass

    def from_file(self, _path: str) -> None:  # pragma: no cover - trivial
        return None


setattr(_magic_mod, "Magic", _DummyMagic)
sys.modules.setdefault("magic", _magic_mod)
