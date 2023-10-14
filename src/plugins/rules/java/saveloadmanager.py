from __future__ import annotations

from ..saveloadmanager import SaveLoadManager as BaseSaveLoadManager


class SaveLoadManager(BaseSaveLoadManager):
    __slots__ = ()
    FILE_TYPES:tuple[(str, str)] = (("Java file", "*.java"),
                                    ("All types", "*"))