from __future__ import annotations

from .de import MESSAGES as DE
from .en import MESSAGES as EN
from .fr import MESSAGES as FR
from .hi import MESSAGES as HI
from .it import MESSAGES as IT
from .ko import MESSAGES as KO
from .nl import MESSAGES as NL
from .pt import MESSAGES as PT
from .uk import MESSAGES as UK
from .zh import MESSAGES as ZH

TRANSLATIONS = {
    "de": DE,
    "en": EN,
    "fr": FR,
    "hi": HI,
    "it": IT,
    "ko": KO,
    "nl": NL,
    "pt": PT,
    "uk": UK,
    "zh": ZH,
}

__all__ = ["TRANSLATIONS"]
