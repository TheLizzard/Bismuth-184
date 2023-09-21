from __future__ import annotations
import tkinter as tk
import string

from .baserule import Rule

DEBUG:bool = False
# tk.Event.state constants
SHIFT:int = 1
ALT:int = 8
CTRL:int = 4
ALPHANUMERIC_ = string.ascii_letters + string.digits + "_"
MOUSE_DRAG_PIXELS:int = 10
SCROLL_SPEED:int = 1

SEL_TAG:str = "selected" # Copied from PythonPlugin


class SelectManager(Rule):
    __slots__ = "text", "old_sel_fg", "old_sel_bg", "old_inactivebg"
    REQUESTED_LIBRARIES:tuple[str] = "event_generate", "bind", "unbind"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs = (
                # Arrow
                "<Left>", "<Right>", "<Up>", "<Down>",
                # Mouse
                "<Button-1>", "<Double-Button-1>", "<Triple-Button-1>",
                "<B1-Motion>",
                # User/program input
                "<<Before-Insert>>", "<<After-Insert>>", "<<After-Delete>>",
                # [<before-delete> can't call delete_selection()]
                # Backspace to stop other rules from handling it if selsected
                "<BackSpace>", "<Delete>",
                # Moving the insert mark should also move the linsert mark
                #   most of the time
                "<<Move-Insert>>",
              )
        super().__init__(plugin, text, evs)
        self.text:tk.Text = self.widget

    def attach(self) -> None:
        super().attach()
        self.old_sel_fg = self.text.tag_cget("sel", "foreground")
        self.old_sel_bg = self.text.tag_cget("sel", "background")
        self.text.tag_config("sel", background="", foreground="")
        self.old_inactivebg:str = self.text.cget("inactiveselectbackground")
        self.text.config(inactiveselectbackground=self.text.cget("bg"))
        self.text.tag_config(SEL_TAG, background="orange", foreground="white")
        self.text.tag_raise(SEL_TAG)

    def detach(self) -> None:
        super().detach()
        self.text.tag_config("sel", background=self.old_sel_bg,
                                    foreground=self.old_sel_fg)
        self.text.config(inactiveselectbackground=self.old_inactivebg)

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        if on in ("backspace", "delete"):
            start, end = self.plugin.get_selection()
            if start == end:
                return False
        idx:str = None
        drag:tuple = None
        data:tuple = None

        if on.endswith("button-1"):
            on:str = on.removesuffix("button-1") + "mouse"
            idx:str = self.text.index(f"@{event.x},{event.y}")

        elif on == "b1-motion":
            on:str = "mouse-motion"
            idx:str = self.text.index(f"@{event.x},{event.y}")
            width:int = self.text.winfo_width()
            height:int = self.text.winfo_height()
            drag_x = drag_y = 0
            if event.x < MOUSE_DRAG_PIXELS:
                drag_x:int = -1
            elif event.x > width-MOUSE_DRAG_PIXELS:
                drag_x:int = +1
            if event.y < MOUSE_DRAG_PIXELS:
                drag_y:int = -1
            elif event.y > height-MOUSE_DRAG_PIXELS:
                drag_y:int = +1
            drag:tuple = drag_x, drag_y

        if on == "<before-insert>":
            if event.data[2] is not None:
                return False

        if on == "<move-insert>":
            data:tuple = event.data

        return on, event.state&CTRL, event.state&SHIFT, idx, drag, data, True

    def do(self, _, on, ctrl, shift, idx:str, drag:tuple, data:tuple) -> Break:
        if on in ("backspace", "delete"):
            self.plugin.delete_selection()
            return True

        if on == "<move-insert>":
            idx:str = data[0]
            if DEBUG: print(f"[DEBUG]: insert set {idx}")
            self.text.see(idx)
            if idx != "insert":
                self.text.mark_set("insert", idx)
            # Set linsert unless specifically told not to:
            if (len(data) == 1) or (not data[1]):
                if DEBUG: print(f"[DEBUG]: linsert set {idx}")
                self.text.mark_set("linsert", idx)
            return False

        if on == "mouse":
            self.plugin.remove_selection()
            self.text.mark_set("mouse-start", idx)
            self.text.event_generate("<<Add-Separator>>")
            self.text.event_generate("<<Move-Insert>>", data=(idx,))
            return False

        if on == "double-mouse":
            self.plugin.remove_selection()
            start:str = self.get_movement("left", True, idx, text=True)
            end:str = self.get_movement("right", True, idx, text=True)
            self.plugin.set_selection(start, end)
            self.text.event_generate("<<Move-Insert>>", data=(end,))
            return True

        if on == "triple-mouse":
            return True

        if on == "mouse-motion":
            delta:str = None
            if drag[0] != 0:
                delta:str = f"{SCROLL_SPEED*drag[0]}c"
            elif drag[1] != 0:
                delta:str = f"{SCROLL_SPEED*drag[1]}l"
            if delta is not None:
                self.text.see(f"{idx} +{delta}")
            start, end = self.plugin.order_idxs(idx, "mouse-start")
            self.plugin.set_selection(start, end)
            self.text.event_generate("<<Move-Insert>>", data=(idx,))
            return True

        if on == "<before-insert>":
            self.plugin.delete_selection()
            return False

        if on in ("<after-insert>", "<after-delete>"):
            self.text.event_generate("<<Move-Insert>>", data=("insert",))
            if on == "<after-delete>":
                self.plugin.delete_selection()
            return False

        cur:str = self.text.index("insert")
        new:str = self.get_movement(on, ctrl, cur)

        if on in ("left", "right"):
            start, end = self.plugin.get_selection()
            if (start == end) or shift:
                if self.text.compare(new, "==", "end"):
                    new:str = "end -1c"
            else:
                new:str = start if on == "left" else end

        elif on not in ("up", "down"):
            raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")

        if shift:
            start, end = self.plugin.get_selection()
            # Calculate the new selection range
            newstart, newend = self.sel_calc(start, end, cur, new)
            if self.text.compare(newend, "==", "end"):
                newend:str = self.text.index("end -1c")
                self.text.event_generate("<<Move-Insert>>", data=(newend,))
            self.plugin.set_selection(newstart, newend)
        else:
            self.plugin.remove_selection()

        self.text.see(new)
        nolinsert:bool = on in ("up", "down")
        self.text.event_generate("<<Move-Insert>>", data=(new, nolinsert))
        self.text.event_generate("<<Add-Separator>>")
        return True

    def get_movement(self, arrow:str, ctrl, cur:str, text:bool=False) -> str:
        if (not ctrl) or (arrow in ("up", "down")):
            if arrow == "left":
                return f"{cur} -1c"
            elif arrow == "right":
                return f"{cur} +1c"
            elif arrow == "up":
                # If at the top line
                if cur.split(".")[0] == "1":
                    if DEBUG: print("[DEBUG]: linsert set [new == 1.0]")
                    self.text.mark_set("linsert", "1.0")
                    return f"{cur} linestart"
                charsin:str = self.text.index("linsert").split(".")[1]
                # Move the cursor up one line
                new:str = f"{cur} -1l linestart +{charsin}c"
                if self.text.compare(new, ">", f"{cur} -1l lineend"):
                    return f"{cur} -1l lineend"
                return f"{cur} -1l linestart +{charsin}c"
            elif arrow == "down":
                charsin:str = self.text.index("linsert").split(".")[1]
                # Move the cursor down one line
                new:str = f"{cur} +1l linestart +{charsin}c"
                if self.text.compare(f"{cur} lineend", "==", "end -1c"):
                    if DEBUG: print("[DEBUG]: linsert set [new == end-1c]")
                    self.text.mark_set("linsert", "end -1c")
                if self.text.compare(new, ">", f"{cur} +1l lineend"):
                    return f"{cur} +1l lineend"
                return f"{cur} +1l linestart +{charsin}c"
        else:
            if arrow == "left":
                size:int = self.get_word_size(-1, cur, "1.0", text)
                return f"{cur} -{size}c"
            elif arrow == "right":
                size:int = self.get_word_size(+1, cur, "end", text)
                return f"{cur} +{size}c"

    def get_word_size(self, strides, start, stop, text:bool=False) -> int:
        assert abs(strides) == 1, "ValueError"
        chars_skipped:int = 0
        # Check what we are looking for:
        if strides > 0:
            current_char:str = self.text.get(start, start+"+1c")
        else:
            current_char:str = self.text.get(start+"-1c", start)
        looking_for_alphabet:bool = current_char not in ALPHANUMERIC_
        if looking_for_alphabet and text:
            new_start:str = f"{start} +{-strides}c"
            return self.get_word_size(strides, new_start, stop, text=False) - 1
        if current_char in "'\"(){}[]\n":
            return 1

        while looking_for_alphabet ^ (current_char in ALPHANUMERIC_):
            chars_skipped += 1
            left:str = f"{start} +{chars_skipped*strides}c"
            right:str = f"{start} +{(chars_skipped+1)*strides}c"
            if strides < 0:
                left, right = right, left
            current_char:str = self.text.get(left, right)
            if current_char in "'\"(){}[]\n":
                break
        return chars_skipped

    def sel_calc(self, start:str, end:str, cur:str, new:str) -> tuple[str,str]:
        # Nothing selected
        if start == end:
            return self.plugin.order_idxs(cur, new)
        # selection's start changing
        if cur == start:
            return self.plugin.order_idxs(new, end)
        # selection's end changing
        if cur == end:
            return self.plugin.order_idxs(start, new)
        # Cursor not inside selection
        return self.plugin.order_idxs(cur, new)