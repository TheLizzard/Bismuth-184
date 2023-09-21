from __future__ import annotations

from ..commentmanager import CommentManager as BaseCommentManager


class CommentManager(BaseCommentManager):
    COMMENT_STR:str = "#"