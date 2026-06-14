from __future__ import annotations

from .en import MESSAGES as EN
from .pt import MESSAGES as PT
from .zh import MESSAGES as ZH

TRANSLATIONS = {
    "en": EN,
    "zh": ZH,
    "pt": PT,
}

__all__ = ["TRANSLATIONS"]
