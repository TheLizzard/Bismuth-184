from __future__ import annotations

from ..saveloadmanager import SaveLoadManager as BaseSaveLoadManager


class SaveLoadManager(BaseSaveLoadManager):
    __slots__ = ()
    FILE_TYPES:tuple[(str, str)] = (("All types", "*"),
                                    ("Shell script", "*.sh"),
                                    ("Run file", "*.run"))
