from __future__ import annotations

from ..whitespacemanager import WhiteSpaceManager as BaseWhiteSpaceManager


class WhiteSpaceManager(BaseWhiteSpaceManager):
    __slots__ = ()
    INDENTATION_DELTAS:dict[str,int] = {"{":+1}
    INDENTATION_CP:set[str] = {"(", "["}

    def return_pressed(self, shift:bool) -> tuple[Break,str]:
        brackets:bool = "{}" == self.text.get("insert -1c", "insert +1c")
        ret, ind_before = super().return_pressed(shift)
        if brackets and (not shift):
            insert:str = self.text.index("insert")
            self.text.insert("insert", "\n"+ind_before)
            self.text.mark_set("insert", insert)
        return ret, ind_before