from __future__ import annotations

from ..whitespacemanager import WhiteSpaceManager as BaseWhiteSpaceManager


class WhiteSpaceManager(BaseWhiteSpaceManager):
    __slots__ = ()
    INDENTATION_DELTAS:dict[str,int] = {"{":+1, ":":+1}