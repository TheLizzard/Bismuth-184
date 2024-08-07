from __future__ import annotations
import tkinter as tk
import string

from .baserule import Rule, SHIFT, ALT, CTRL
from settings.settings import curr as settings

DEBUG:bool = False
MOUSE_DRAG_PIXELS:int = 10
SCROLL_SPEED:int = 1

MOUSE_START_MARK:str = "mouse_start"


class SelectManager(Rule):
    __slots__ = "text", "old_sel_fg", "old_sel_bg", "old_inactivebg", \
                "selecting", "set_linsert"
    REQUESTED_LIBRARIES:tuple[str] = "insertdel_events"
    REQUESTED_LIBRARIES_STRICT:bool = True

    def __init__(self, plugin:BasePlugin, text:tk.Text) -> Rule:
        evs = (
                # Arrow
                "<Left>", "<Right>", "<Up>", "<Down>",
                # Other keyboard buttons
                "<Home>", "<End>", "<KP_End>", "<KP_Home>", "<KP_1>", "<KP_7>",
                # Mouse
                "<Double-Button-1>", "<Triple-Button-1>",
                "<ButtonPress-1>", "<ButtonRelease-1>", "<B1-Motion>",
                # User/program input
                "<<Before-Insert>>", "<<After-Insert>>", "<<After-Delete>>",
                # Backspace to stop other rules from handling it if selsected
                "<BackSpace>", "<Delete>",
                # Moving the insert mark should also move the linsert mark
                #   most of the time
                "<<Insert-Moved>>",
              )
        super().__init__(plugin, text, evs)
        self.text:tk.Text = self.widget
        self.set_linsert:bool = True
        self.selecting:bool = False

    def attach(self) -> None:
        super().attach()
        self.old_sel_fg = self.text.tag_cget("sel", "foreground")
        self.old_sel_bg = self.text.tag_cget("sel", "background")
        self.text.tag_config("sel", background="cyan", foreground="")
        self.old_inactivebg:str = self.text.cget("inactiveselectbackground")
        self.text.config(inactiveselectbackground=self.text.cget("bg"))
        self.text.tag_config(self.plugin.SEL_TAG, foreground="white",
                             background=settings.editor.selectmanager.bg)
        self.text.mark_set(MOUSE_START_MARK, "insert")
        self.text.tag_raise(self.plugin.SEL_TAG)

    def detach(self) -> None:
        super().detach()
        self.text.tag_config("sel", background=self.old_sel_bg,
                                    foreground=self.old_sel_fg)
        self.text.config(inactiveselectbackground=self.old_inactivebg)

    @staticmethod
    def get_index_from_pos(text:tk.Text, x:int, y:int) -> str:
        # This function is a wrapper for tk's TextClosestGap function
        # an example of it's implementation:
        #   https://core.tcl-lang.org/tk/tktview?name=b461c70399
        #   /usr/share/tcltk/tk8.6/text.tcl
        """
        proc ::tk::TextClosestGap {w x y} {
            set pos [$w index @$x,$y]
            set bbox [$w bbox $pos]
            if {$bbox eq ""} {
                return $pos
            }
            if {($x - [lindex $bbox 0]) < ([lindex $bbox 2]/2)} {
                return $pos
            }
            $w index "$pos + 1i"
        }
        """
        idx:str = text.index(f"@{x},{y}")
        # In later versions of Tcl if they fix this
        if text.compare(idx, "==", f"{idx} display lineend"):
            return idx
        return str(text.tk.call("::tk::TextClosestGap", text._w, x, y))

    def applies(self, event:tk.Event, on:str) -> tuple[...,Applies]:
        ctrl:bool = event.state & CTRL
        shift:bool = event.state & SHIFT
        alt:bool = event.state & ALT

        if on in ("backspace", "delete"):
            start, end = self.plugin.get_selection()
            if start == end:
                return False
        idx:str = None
        drag:tuple = None

        # Double/Triple click
        if on.endswith("button-1"):
            idx:int = self.get_index_from_pos(self.text, event.x, event.y)
            on:str = on.removesuffix("button-1") + "mouse"

        # Mouse press/release
        elif on.startswith("button") and on.endswith("-1"):
            idx:int = self.get_index_from_pos(self.text, event.x, event.y)
            on:str = "mouse-" + on.removeprefix("button").removesuffix("-1")

        # Mouse select
        elif on == "b1-motion":
            on:str = "mouse-motion"
            idx:int = self.get_index_from_pos(self.text, event.x, event.y)
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

        # If there are any tags in the insert, don't delete selected text
        elif on == "<before-insert>":
            if len(event.data["raw"][2]):
                return False

        # Set linsert only if `self.set_linsert` is `True`
        elif on == "<insert-moved>":
            if not self.set_linsert:
                return False
            on:str = "<set-linsert>"

        # Keypad home/end
        elif on.startswith("kp_"):
            on:str = on.removeprefix("kp_")
            if shift:
                on:str = {"end":"1", "home":"7"}.get(on, on)
            if on in ("1", "7"):
                if not ctrl:
                    return False
                on:str = {"1":"end", "7":"home"}.get(on, on)
                ctrl:bool = alt

        return on, ctrl, shift, idx, drag, True

    def do(self, _, on, ctrl:bool, shift:bool, idx:str, drag:tuple) -> Break:
        if on in ("backspace", "delete"):
            self.plugin.delete_selection()
            return True

        if on == "<set-linsert>":
            self.text.mark_set("linsert", "insert")
            return False

        if on == "mouse-press":
            self.text.focus_set()
            self.selecting:bool = True
            self.plugin.remove_selection()
            self.text.mark_set(MOUSE_START_MARK, idx)
            self.text.event_generate("<<Add-Separator>>")
            self.text.event_generate("<<CancelAll>>")
            self.plugin.move_insert(idx)
            self.text.focus_set()
            return True

        if on == "mouse-release":
            if self.selecting:
                self.selecting:bool = False
                return True
            return False

        if on == "double-mouse":
            self.plugin.remove_selection()
            start:str = self.get_movement("left", True, "insert", text=True)
            end:str = self.get_movement("right", True, "insert", text=True)
            self.plugin.set_selection(start, end)
            self.plugin.move_insert(end)
            return True

        if on == "triple-mouse":
            return True

        if on == "mouse-motion":
            if not self.selecting:
                return False
            # reimplement this using `xview`/`yview`
            delta:str = None
            if drag[0] != 0:
                delta:str = f"{SCROLL_SPEED*drag[0]}c"
                if self.text.compare(idx, "==", f"{idx} lineend"):
                    if drag[0] > 0:
                        delta:str = None
                if self.text.compare(idx, "==", f"{idx} linestart"):
                    if drag[0] < 0:
                        delta:str = None
            elif drag[1] != 0:
                delta:str = f"{SCROLL_SPEED*drag[1]}l"
            if delta is not None:
                self.text.see(f"{idx} +{delta}")
            start, end = self.plugin.order_idxs(MOUSE_START_MARK, idx)
            self.plugin.set_selection(start, end)
            self.plugin.move_insert(idx)
            return True

        if on == "<before-insert>":
            self.plugin.delete_selection()
            return False

        if on in ("<after-insert>", "<after-delete>"):
            self.plugin.move_insert("insert")
            if on == "<after-delete>":
                self.plugin.delete_selection()
            return False

        # Selection stuff
        cur:str = self.text.index("insert")
        new:str = self.get_movement(on, ctrl, cur)
        # Home/End
        if on in ("home", "end"):
            pass
        # Left/Right
        elif on in ("left", "right"):
            start, end = self.plugin.get_selection()
            if (start == end) or shift:
                if self.text.compare(new, "==", "end"):
                    new:str = "end -1c"
            else:
                new:str = start if on == "left" else end
        # Up/Down
        elif on in ("up", "down"):
            pass
        # Unknown
        else:
            raise RuntimeError(f"Unhandled {on} in {self.__class__.__name__}")
        # Actual computation
        if shift:
            start, end = self.plugin.get_selection()
            # Calculate the new selection range
            newstart, newend = self.sel_calc(start, end, cur, new)
            if self.text.compare(newend, "==", "end"):
                newend:str = self.text.index("end -1c")
                self.plugin.move_insert(newend)
            self.plugin.set_selection(newstart, newend)
        else:
            self.plugin.remove_selection()

        # DON'T move around these lines of code
        self.set_linsert:bool = on not in ("up", "down")
        self.plugin.move_insert(new)
        self.set_linsert:bool = True
        self.text.event_generate("<<Add-Separator>>")
        return True

    def get_movement(self, arrow, ctrl:bool, cur:str, text:bool=False) -> str:
        if ctrl:
            # Left/Right
            if arrow == "left":
                size:int = self.get_word_size(-1, cur, "1.0", text)
                return f"{cur} -{size}c"
            elif arrow == "right":
                size:int = self.get_word_size(+1, cur, "end -1c", text)
                return f"{cur} +{size}c"
            # Up/Down
            elif arrow == "up":
                size:int = self.get_para_size(-1, cur, "1.0")
                return f"{cur} -{size}l linestart"
            elif arrow == "down":
                size:int = self.get_para_size(+1, cur, "end -1c")
                return f"{cur} +{size}l lineend"
            # Home/End
            elif arrow == "home":
                return "1.0"
            elif arrow == "end":
                return "end -1c"
        else:
            # Left/Right
            if arrow == "left":
                return f"{cur} -1c"
            elif arrow == "right":
                return f"{cur} +1c"
            # Up/Down
            elif arrow == "up":
                if cur.split(".")[0] == "1":
                    if DEBUG: print("[DEBUG]: linsert set [new == 1.0]")
                    self.text.mark_set("linsert", "1.0")
                    return f"{cur} linestart"
                charsin:str = self.text.index("linsert").split(".")[1]
                new:str = f"{cur} -1l linestart +{charsin}c"
                if self.text.compare(new, ">", f"{cur} -1l lineend"):
                    return f"{cur} -1l lineend"
                return f"{cur} -1l linestart +{charsin}c"
            elif arrow == "down":
                charsin:str = self.text.index("linsert").split(".")[1]
                new:str = f"{cur} +1l linestart +{charsin}c"
                if self.text.compare(f"{cur} lineend", "==", "end -1c"):
                    if DEBUG: print("[DEBUG]: linsert set [new == end-1c]")
                    self.text.mark_set("linsert", "end -1c")
                if self.text.compare(new, ">", f"{cur} +1l lineend"):
                    return f"{cur} +1l lineend"
                return f"{cur} +1l linestart +{charsin}c"
            # Home/End
            elif arrow == "home":
                line:str = self.text.get(f"{cur} linestart", cur)
                if len(line) == 0:
                    line:str = self.text.get(cur, f"{cur} lineend")
                spaces:int = len(line) - len(line.lstrip(" \t"))
                if spaces == len(line):
                    spaces:int = 0
                return f"{cur} linestart +{spaces}c"
            elif arrow == "end":
                fline:str = self.text.get(f"{cur} linestart", f"{cur} lineend")
                line:str = self.plugin.get_virline(f"{cur} lineend")
                cur_char:int = int(self.text.index(cur).split(".")[1])
                if (cur_char < len(line)) or (len(fline) == cur_char):
                    comment:int = len(fline) - len(line)
                    if len(fline.rstrip(" \t")) == len(line):
                        return f"{cur} lineend"
                    else:
                        return f"{cur} lineend -{comment}c"
                else:
                    return f"{cur} lineend"
        raise NotImplementedError(f"Unreachable {ctrl=!r} {arrow=!r}")

    def get_word_size(self, strides, start, stop, text:bool=False) -> int:
        assert abs(strides) == 1, "ValueError"
        chars_skipped:int = 0
        # Check what we are looking for:
        if strides > 0:
            left, right = start, f"{start} +1c"
        else:
            left, right = f"{start} -1c", start
            if self.text.compare(start, "==", f"{start} lineend"):
                iscomment:bool = self.plugin.left_has_tag("comment", start)
        cur:str = self.text.get(left, right)
        isalpha = lambda s: s.isidentifier() or s.isdigit()
        iscomment = lambda loc: self.plugin.left_has_tag("comment", loc)
        looking_for_comment:bool = not self.plugin.left_has_tag("comment",
                                                                start)
        looking_for_alphabet:bool = not isalpha(cur)
        looking_for_space:bool = not (cur == " ")
        if looking_for_alphabet and text:
            new_start:str = f"{start} +{-strides}c"
            return self.get_word_size(strides, new_start, stop, text=False) - 1

        while (looking_for_alphabet ^ isalpha(cur)) and \
              (looking_for_space ^ (cur == " ")) and \
              (cur not in "'\"(){}[]\n") and \
              (looking_for_comment ^ iscomment(right if strides > 0 else left)):
            chars_skipped += 1
            left:str = f"{start} +{chars_skipped*strides}c"
            right:str = f"{start} +{(chars_skipped+1)*strides}c"
            if strides < 0:
                left, right = right, left
            cur:str = self.text.get(left, right)
        return max(1, chars_skipped)

    def get_para_size(self, strides:int, start:str, stop:str) -> int:
        cur:str = start
        lines_skipped:int = 0
        while True:
            if self.text.compare(f"{cur} linestart", "==", f"{stop} linestart"):
                break
            cur:str = self.text.index(f"{cur} +{strides}l")
            lines_skipped += 1
            if not self.text.get(f"{cur} linestart", f"{cur} lineend"):
                break
        return lines_skipped

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