from __future__ import annotations
import tkinter as tk

WARNINGS:bool = False


class VirtualEvent:
    __slots__ = "data", "state", "char", "keysym", "x", "y", "num", "delta", \
                "focus", "width", "height", "widget"

    def __init__(self, widget:tk.Misc, **kwargs:dict):
        self.widget:tk.Misc = kwargs.pop("widget", widget)
        self.focus:tk.Misc = kwargs.pop("focus", None)
        self.keysym:str = kwargs.pop("keysym", "")
        self.height:int = kwargs.pop("height", 0)
        self.data:tuple = kwargs.pop("data", ())
        self.width:int = kwargs.pop("width", 0)
        self.state:int = kwargs.pop("state", 0)
        self.delta:int = kwargs.pop("delta", 0)
        self.char:str = kwargs.pop("char", "")
        self.num:int = kwargs.pop("num", 0)
        self.x:int = kwargs.pop("x", 0)
        self.y:int = kwargs.pop("y", 0)
        if len(kwargs) != 0:
            raise TypeError(f"{self.__class__.__name__} got an unexpected " \
                            f"keyword arguments {tuple(kwargs.keys())}")


class _VirtualEvents:
    __slots__ = "widget", "virtual_events", "paused", \
                "old_bind", "old_unbind", "old_event_generate", \
                "old_bind_all", "old_unbind_all"

    def __init__(self, widget:tk.Misc) -> None:
        assert not getattr(widget, "virtual_events", None), "InternalError"
        self.widget:tk.Misc = widget
        self.virtual_events:dict[str,list[tuple[Function,bool]]] = dict()
        self.paused:bool = False

        self.old_event_generate = self.widget.event_generate
        self.widget.event_generate = self.send
        self.old_bind = self.widget.bind
        self.widget.bind = self.bind
        self.old_unbind = self.widget.unbind
        self.widget.unbind = self.unbind
        self.old_bind_all = self.widget.bind_all
        self.widget.bind_all = self.bind_all
        self.old_unbind_all = self.widget.unbind_all
        self.widget.unbind_all = self.unbind_all

    def __new__(Cls:type, widget:tk.Misc, *args, **kwargs) -> VirtualEvents:
        if widget.bind.__self__.__class__ == Cls:
            return widget.virtual_events
        else:
            return super().__new__(Cls, *args, **kwargs)

    def send(self, event_name:str, *, drop:bool=True, other:bool=False,
             **kwargs:dict) -> str:
        if (not other) and drop:
            ret:str = self._send_rest(event_name, drop=False, **kwargs)
            if ret in ("break", "handled"):
                return ret
        virtual:bool = event_name.startswith("<<") and event_name.endswith(">>")
        if virtual:
            funcs = self.virtual_events.get(event_name, [])
            # If there are no function bound to that event drop to the old
            #   event_generate
            if len(funcs) == 0:
                if WARNINGS and drop:
                    print(f"[WEARNING]: No handlers for {event_name} so " \
                          "sending to original event_generate.")
            elif self.paused and (not event_name.lower().startswith("<<raw-")):
                return ""
            else:
                event:VirtualEvent = VirtualEvent(self.widget, **kwargs)
                handled:bool = False
                for func, all in funcs:
                    if all or (not other):
                        try:
                            result:str = func(event)
                        except Exception as error:
                            if hasattr(tk, "report_full_exception"):
                                tk.report_full_exception(self.widget, error)
                            else:
                                self.widget._report_exception()
                        else:
                            handled:bool = True
                            if result == "break":
                                return "break"
                return "handled" if handled else ""
        # If [the event is not virtual or no event handlers are bound to that
        #   event] and drop is True, use the old `event_generate`
        if drop:
            return self.old_event_generate(event_name, **kwargs)

    def bind(self, event_name:str, func, *, add=False, all:bool=False) -> str:
        virtual:bool = event_name.startswith("<<") and event_name.endswith(">>")
        if virtual:
            if event_name not in self.virtual_events:
                self.virtual_events[event_name] = []
            if not add:
                self.virtual_events[event_name].clear()
            self.virtual_events[event_name].append((func, all))
            drop_func = lambda e: self.send(event_name, drop=False)
            if all:
                self.old_bind_all(event_name, drop_func, add=add)
            else:
                self.old_bind(event_name, drop_func, add=add)
            return self.func_to_id(func, all)
        else:
            if all:
                return self.old_bind_all(event_name, func, add=add)
            else:
                return self.old_bind(event_name, func, add=add)

    def unbind(self, event_name:str, id:str, *, all:bool=False) -> None:
        if event_name in self.virtual_events:
            func_list:list[Function] = self.virtual_events.get(event_name, [])
            for i, (func, all) in enumerate(func_list):
                if self.func_to_id(func, all) == id:
                    func_list.pop(i)
                    if len(func_list) == 0:
                        self.virtual_events.pop(event_name)
                    return None
            if WARNING:
                print(f"[WARNING]: unbind({event_name}) is dropping down to " \
                      "the tkinter unbind, even though this event is managed " \
                      f"by {self.__class__.__name__}")
        if all:
            self.old_unbind_all(event_name, id)
        else:
            self.old_unbind(event_name, id)

    def bind_all(self, event_name:str, func:Function, *, add:bool=True) -> str:
        return self.bind(event_name, func, add=add, all=True)

    def unbind_all(self, event_name:str, id:str) -> None:
        self.unbind(event_name, id, all=True)

    @staticmethod
    def func_to_id(function:Function, all:bool) -> str:
        """
        This function is essentially a hash function from any callable to
          str. This must be improved by looking/copying from
          tkinter/__init__.py@Variable._register
        """
        return str(id(function)) + str(int(all))

    def _send_rest(self, event_name:str, **kwargs:dict) -> str:
        ret:str = ""
        for vir_event in _vir_events.values():
            if vir_event == self:
                continue
            new_ret:str = vir_event.send(event_name, other=True, **kwargs)
            if new_ret == "break":
                return "break"
            if new_ret == "handled":
                ret:str = "handled"
        return ret


_vir_events:dict[widget:tk.Misc:_VirtualEvents] = {}
def VirtualEvents(widget:tk.Misc) -> _VirtualEvents:
    if widget not in _vir_events:
        _vir_events[widget] = _VirtualEvents(widget)
    return _vir_events[widget]