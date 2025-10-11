from .rules.baserule import Rule
from .rules.wrapmanager import WrapManager
from .rules.undomanager import UndoManager
from .rules.umarkmanager import UMarkManager
from .rules.selectmanager import SelectManager
from .rules.bracketmanager import BracketManager
from .rules.shortcutmanager import RemoveShortcuts
from .rules.reparentmanager import ReparentManager
from .rules.settingsmanager import SettingsManager
from .rules.clipboardmanager import ClipboardManager
from .rules.seeinsertmanager import SeeInsertManager
from .rules.controlijklmanager import ControlIJKLManager
from .rules.findreplacemanager import FindReplaceManager
from .rules.insertdeletemanager import InsertDeleteManager
from .rules.xrawidgets import BarManager, LineManager, ScrollbarManager


COMMON_RULES:list[Rule] = [
                            WrapManager,
                            UndoManager,
                            UMarkManager,
                            SelectManager,
                            BracketManager,
                            RemoveShortcuts,
                            SettingsManager,
                            ClipboardManager,
                            SeeInsertManager,
                            ControlIJKLManager,
                            FindReplaceManager,
                            InsertDeleteManager,
                            # Other widgets:
                            ScrollbarManager,
                            ReparentManager,
                            LineManager,
                            BarManager,
                            # MenuManager,
                          ]