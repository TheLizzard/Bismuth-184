from __future__ import annotations

from ..whitespacemanager import WhiteSpaceManager as BaseWhiteSpaceManager


class WhiteSpaceManager(BaseWhiteSpaceManager):
    __slots__ = ()
    INDENTATION_DELTAS:dict[str,int] = {"{":+1} #, ":":+1

    def return_pressed(self, shift:bool) -> tuple[Break,...]:
        brackets:bool = "{}" == self.text.get("insert -1c", "insert +1c")
        ret, *args = super().return_pressed(shift)
        if brackets:
            insert:str = self.text.index("insert")
            size, indentation_type, chars, see_end = args
            self.text.insert("insert", "\n"+size*indentation_type)
            self.text.mark_set("insert", insert)
            if see_end:
                self.text.see("end")
        return ret, *args