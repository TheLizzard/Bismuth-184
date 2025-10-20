from __future__ import annotations
import tkinter as tk

from .baserule import Rule


LOOP_FIX_DELAY:int = 1000 # fix the line number colouring every x ms


class UMarkManager(Rule):
    __slots__ = "text", "_after_id"

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        ons:tuple[str] = (
                           # Toggle umarks
                           "<Control-m>", "<Control-M>"
                           # Goto umark
                           "<Control-8>", "<Control-KP_8>",
                           "<Control-2>", "<Control-KP_2>",
                           # Clear umarks
                           "<<Opened-File>>",
                           # Re-mark
                           "<<Reloaded-File>>",
                         )
        super().__init__(plugin, text, ons=ons)
        self.text:tk.Text = self.widget
        self.text.umarks:set[int] = getattr(self.text, "umarks", set())
        self._after_id:str = None

    # Attach/detach
    def attach(self) -> None:
        super().attach()
        self._fix_loop()
        # self.text.tag_config("umark", background="red") # For debugging

    def detach(self) -> None:
        super().detach()
        if self._after_id:
            self.text.after_cancel(self._after_id)

    # Bindings
    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        return True

    def do(self, on:str) -> Break:
        insert:str = self.text.index("insert")
        line, char = insert.split(".")
        line, char = int(line), int(char)

        if on == "control-m":
            self._toggle_umark(line, char)
            return False

        if on.endswith("2"):
            self._umark_go_down(line, char)
            return False

        if on.endswith("8"):
            self._umark_go_up(line, char)
            return False

        if on == "<opened-file>":
            self._remove_all_umarks()
            return False

        if on == "<reloaded-file>":
            self._fix()
            return False

        raise RuntimeError(f"Unhandled {on!r} in {self.__class__.__qualname__}")

    # Mark helpers
    def _add_umark(self, line:int, char:int) -> None:
        self.text.umarks.add(line)
        self.text.event_generate("<<Set-UMark>>", data=line)
        if char == 0:
            self.text.tag_add("umark", f"{line}.{char}", f"{line}.{char} +1c")
        else:
            self.text.tag_add("umark", f"{line}.{char-1}", f"{line}.{char}")

    def _remove_umark(self, line:int) -> None:
        self.text.umarks.remove(line)
        self.text.event_generate("<<Remove-UMark>>", data=line)
        self.text.tag_remove("umark", f"{line}.0", f"{line}.0 lineend")

    def _remove_all_umarks(self) -> None:
        self.text.umarks.clear()
        self.text.tag_remove("umark", "1.0", "end")
        self.text.event_generate("<<Remove-All-UMarks>>")

    def _toggle_umark(self, line:int, char:int) -> None:
        if self.text.tag_nextrange("umark", f"{line}.0", f"{line}.0 lineend"):
            self._remove_umark(line)
        else:
            self._add_umark(line, char)

    # Move insert up/down
    def _umark_go_down(self, line:int, char:int) -> None:
        self._umark_go_up_down(line, char, False)

    def _umark_go_up(self, line:int, char:int) -> None:
        self._umark_go_up_down(line, char, True)

    def _umark_go_up_down(self, line:int, char:int, up:bool) -> None:
        endline:str = int(self.text.index("end").split(".")[0])
        if up:
            _range:tuple = self.text.tag_prevrange("umark", "insert linestart")
        else:
            _range:tuple = self.text.tag_nextrange("umark", "insert lineend")
        if not _range: return None
        target:str = _range[0] if _range[0].endswith(".0") else _range[1]
        self.plugin.move_insert(target)

    # Fix loop
    def _fix_loop(self) -> None:
        self._after_id:str = None
        if not self.attached: return None
        self._fix()
        self._after_id:str = self.text.after(LOOP_FIX_DELAY, self._fix_loop)

    def _fix(self) -> None:
        now:set[int] = set(self.text.umarks)
        get_line = lambda _range: int(_range[0].split(".")[0])
        target:set[int] = set(map(get_line, self._umark_ranges()))
        for line in target - now:
            self.text.event_generate("<<Set-UMark>>", data=line)
            self.text.umarks.add(line)
        for line in now - target:
            self.text.event_generate("<<Remove-UMark>>", data=line)
            self.text.umarks.remove(line)

    def _umark_ranges(self) -> list[tuple[str,str]]:
        _ranges:list[str] = list(map(str, self.text.tag_ranges("umark")))
        return list(zip(_ranges[::2], _ranges[1::2]))

    # State loading/saving
    def get_state(self) -> object:
        output:list[list[int]] = []
        for _range in self._umark_ranges():
            target:str = _range[0] if _range[0].endswith(".0") else _range[1]
            line, char = target.split(".")
            line, char = int(line), int(char)
            output.append([line,char])
        return output

    def set_state(self, state:object) -> None:
        if not isinstance(state, list): return None
        for line in state:
            if not isinstance(line, list): return None
            if len(line) != 2: return None
            if not isinstance(line[0], int): return None
            if not isinstance(line[1], int): return None
        self._load_umarks(dict(state))

    def _load_umarks(self, marks:dict[int:int]) -> None:
        for line, char in marks.items():
            self._add_umark(line, char)
