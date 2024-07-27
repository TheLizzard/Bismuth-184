from __future__ import annotations
from idlelib.percolator import Percolator
from idlelib.delegator import Delegator
import tkinter as tk

from .baserule import Rule


# /usr/lib/python3.10/idlelib/delegator.py
# /usr/lib/python3.10/idlelib/colorizer.py
# /usr/lib/python3.10/idlelib/percolator.py
class InsertDeleteManager(Rule, Delegator):
    __slots__ = "text"
    REQUESTED_LIBRARIES:tuple[str] = "event_generate"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> InsertDeleteManager:
        super().__init__(plugin, text, ons=())
        Delegator.__init__(self)
        self.text:tk.Text = text

    def attach(self) -> None:
        super().attach()
        if not hasattr(self.text, "percolator"):
            self.text.percolator:Percolator = Percolator(self.text)
        self.text.percolator.insertfilter(self)
        self.text.insertdel_events:bool = True

    def detach(self) -> None:
        super().detach()
        self.text.insertdel_events:bool = False
        self.text.percolator.removefilter(self)

    def insert(self, index:str, chars:str, tags:tuple[str]|str=None) -> None:
        _tags:tuple[str] = (tags,) if isinstance(tags, str) else tags
        _tags:tuple[str] = () if _tags is None else _tags
        data:dict[str:tuple] = {"raw": (index,chars,_tags)}
        data["abs"] = (self._index(index), chars, _tags)
        self.text.event_generate("<<Raw-Before-Insert>>", data=data)
        self.text.event_generate("<<Before-Insert>>", data=data)
        self.delegate.insert(index, chars, tags)
        self.text.event_generate("<<After-Insert>>", data=data)
        self.text.event_generate("<<Raw-After-Insert>>", data=data)

    def delete(self, index1:str, index2:str=None) -> None:
        data:dict[str:tuple[str,str|None]] = {"raw": (index1,index2)}
        data["abs"] = (self._index(index1), self._index(index2))
        self.text.event_generate("<<Raw-Before-Delete>>", data=data)
        self.text.event_generate("<<Before-Delete>>", data=data)
        self.delegate.delete(index1, index2)
        self.text.event_generate("<<After-Delete>>", data=data)
        self.text.event_generate("<<Raw-After-Delete>>", data=data)

    def _index(self, idx:str|None) -> str|None:
        if idx is None:
            return None
        idx:str = self.text.index(idx)
        if idx.split(".")[1] == "0": # Slight optimisation
            if self.text.compare(idx, "==", "end"):
                idx:str = self.text.index("end -1c")
        return idx