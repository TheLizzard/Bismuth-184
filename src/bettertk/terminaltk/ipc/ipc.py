from __future__ import annotations
from threading import Thread, Lock, Event as _Event
from contextlib import contextmanager
from typing import Callable
from time import sleep
import tempfile

try:
    from .tmpfs.os_tools import *
    from . import serialiser
except ImportError:
    from tmpfs.os_tools import *
    import serialiser


EventType:type = str
Threaded:type = bool
Location:type = str
BindID:type = int
Break:type = bool
Pid:type = int
Handler:type = Callable["Event",Break|None]
EventBindings:type = list[tuple[Threaded,Handler]]

_TMP_FOLDER:str = tempfile.gettempdir()


def format_to_permutation(format:str) -> Iterable[str]:
    if "%d" not in format:
        yield format
    else:
        for i in range(9):
            subformat:str = str_rreplace(format, "%d", str(i))
            yield from format_to_permutation(subformat)

def str_rreplace(string:str, search:str, replace:str) -> str:
    # https://stackoverflow.com/a/9943875/11106801
    return replace.join(string.rsplit(search, 1))

@contextmanager
def lock_wrapper(file:File) -> None:
    try:
        lock_file(file)
        yield None
    finally:
        unlock_file(file)


# Only until I implement something like tmpfs in python
#   which might take a long time :/
import shutil
import os

class TmpFilesystem:
    __slots__ = "normalise"

    def __init__(self, name:str) -> Filesystem:
        assert_type(name, str, "name")
        root:str = os.path.join(_TMP_FOLDER, name)
        self.normalise = lambda path: os.path.join(root, path)
        self.makedir(".", lock=False)

    def open(self, path:str, mode:str, *, lock:bool=True) -> File:
        if lock:
            with self.lock_wrapper("fs_write.lock"):
                return open(self.normalise(path), mode)
        else:
            return open(self.normalise(path), mode)

    @contextmanager
    def lock_wrapper(self, path_or_file:str|File) -> None:
        if isinstance(path_or_file, str):
            path:str = path_or_file
            exists:bool = os.path.exists(self.normalise(path))
            file:File = self.open(path, ("rb" if exists else "wb"), lock=False)
        else:
            file:File = path_or_file
        try:
            with lock_wrapper(file):
                yield None
        finally:
            if isinstance(path_or_file, str):
                file.close()

    def listfiles(self, path:str) -> Iterable[str]:
        _, folders, files = self._walk(path)
        return files

    def _walk(self, path:str) -> tuple[str,tuple[str],tuple[str]]:
        for output in os.walk(self.normalise(path)):
            return output
        return path, [], []

    def listdirs(self, path:str) -> Iterable[str]:
        _, folders, files = self._walk(path)
        return folders

    def listall(self, path:str) -> Iterable[tuple[str,str]]:
        _, folders, files = self._walk(path)
        for folder in folders:
            yield "folder", folder
        for file in files:
            yield "file", file

    def makedir(self, path:str, *, lock:bool=True) -> None:
        if lock:
            with self.lock_wrapper("fs_write.lock"):
                os.makedirs(self.normalise(path), exist_ok=True)
        else:
            os.makedirs(self.normalise(path), exist_ok=True)

    def removedir(self, path:str) -> None:
        with self.lock_wrapper("fs_write.lock"):
            shutil.rmtree(self.normalise(path))

    def removefile(self, path:str) -> None:
        with self.lock_wrapper("fs_write.lock"):
            os.remove(self.normalise(path))

    def join(self, *paths:tuple[str]) -> str:
        return os.path.join(*paths)

    def exists(self, path:str) -> bool:
        return os.path.exists(self.normalise(path))

    def close(self) -> None:
        # TODO: Implement cleanup?
        pass

    def get_free_file(self, folder:str, format:str, mode:str) -> File|None:
        assert "w" in mode, "mode must be write"
        with self.lock_wrapper("fs_write.lock"):
            for perm in format_to_permutation(format):
                path:str = self.join(folder, perm)
                if not self.exists(path):
                    return self.open(path, mode, lock=False)
        return None

    def get_free_folder(self, format:str, *,
                        is_abandoned=lambda*s:0) -> str|None:
        # TODO: race condition between return and folder capture
        with self.lock_wrapper("_empty_name.lock"):
            for perm in format_to_permutation(format):
                if not self.exists(perm) or is_abandoned(self, perm):
                    return perm
            return None


class Event:
    __slots__ = "type", "data", "_from"

    def __init__(self, type:EventType, data:object=None,
                 _from:Location="unknown") -> Event:
        assert_type(type, EventType, "type")
        assert_type(_from, Location, "_from")
        self._from:Location = _from
        self.type:EventType = type
        self.data:object = data

    def __repr__(self) -> str:
        return f"Event({self.type!r}, data={self.data!r}, " \
               f"_from={self._from!r})"

    def serialise(self, **kwargs:dict) -> dict:
        assert_type(self, Event, "event")
        return {"type":self.type, "from":self._from, "data":self.data}

    @classmethod
    def deserialise(Class:type, data:dict, **kwargs:dict) -> Event:
        assert_type(data, dict, "data")
        return Event(data.pop("type"), data.pop("data"), data.pop("from"))

serialiser.register(Event, "ipc.Event", Event.serialise, Event.deserialise)


_sig_to_ipc:dict = {}
def close_all_ipcs() -> None:
    for ipc in _sig_to_ipc.values():
        if not ipc.dead:
            ipc.close()


class IPC:
    __slots__ = "name", "_bindings", "_bindings_lock", "_call_queue", "_fs", \
                "_root", "_bound", "_old_signal", "dead", "sig"

    def __init__(self, name:str, sig) -> IPC:
        if sig in _sig_to_ipc:
            raise ValueError("signal already in use")
        _sig_to_ipc[sig] = self
        self.sig = sig
        self._call_queue:list[tuple[list[Handler],Event]] = []
        self._bindings:dict[EventType:EventBindings] = {}
        self._fs:TmpFilesystem = TmpFilesystem(name)
        self._bindings_lock:Lock = Lock()
        self._root:str = str(SELF_PID)
        self._bound:bool = False
        self._old_signal = None
        self.dead:bool = False
        self.name:str = name
        self._on_init()

    @staticmethod
    def rm_event(func:Callable[Break|None]) -> Callable[Event,Break|None]:
        """
        A higher order function that takes a function that takes no args
        and returns a function that takes 1 arg that is ignored
        """
        def inner(event:Event) -> Break|None:
            return func()
        return inner

    def event_generate(self, event:EventType, *, data:object=None,
                       where:Location="all", timeout:int=1000,
                       ignore_bad_pids:bool=False) -> None:
        """
        Generates an event at a location with arbitrary data.
        The location passed in is resolved into a set of pids by `find_where`
        The timeout passed in is the number of milliseconds to try to send
        the event for before raising a `FileExistsError` (target recieved too
        many messages and hasn't handled them - might have died). The
        `FileExistsError` is raised in another thread for speed reasons
        If `ignore_bad_pids` is true, it ignores and skips timeout errors.
        """
        assert not self.dead, "IPC already closed"

        def inner(pid:int) -> None:
            if pid == SELF_PID:
                self._got_event(event)
            else:
                try:
                    self._send_data(pid, data, timeout=timeout)
                except FileExistsError as error:
                    if not ignore_bad_pids:
                        raise error

        assert_type(where, Location, "where")
        assert_type(event, EventType, "event")
        event:Event = Event(event, data, _from=self._root)
        data:bytes = serialiser.enc_dumps(event)
        threads:list[Thread] = []
        for pid in self.find_where(where):
            thread:Thread = Thread(target=inner, args=(pid,), daemon=True)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

    def bind(self, event:EventType, handler:Handler,
             threaded:Threaded=True) -> None:
        """
        Bind a handler to an event. When this process receives an event
        matching the event passed in, the handler will be called.
        If `threaded` is true, then the handler will be immediately be called
        from a new thread. If `threaded` is false, then the handler will be
        called next time `call_queued_events` is called.
        If a handler returns a truthy, then the handlers registered before it
        will not be called
        """
        assert not self.dead, "IPC already closed"
        assert_type(event, EventType, "event")
        assert_type(handler, Callable, "handler")
        assert_type(threaded, Threaded, "threaded")
        with self._bindings_lock:
            if event not in self._bindings:
                self._bindings[event] = []
            self._bindings[event].insert(0, (threaded,handler))
        self._add_listener(event)

    def unbind(self, event:EventType, handler:Handler=None) -> None:
        """
        Untested method for reversing the effect of `bind` given an event
        and optionally a handler. If no handler is specified, then all
        handlers for the event are unbound.
        """
        assert not self.dead, "IPC already closed"
        if event not in self._bindings:
            raise ValueError("Nothing bound to {event=!r}")
        with self._bindings_lock:
            if handler is None:
                self._bindings[event].clear()
            else:
                for i, (_,h) in enumerate(self._bindings):
                    if h == handler:
                        self._bindings.pop(i)
                        return None

    def find_where(self, where:Location) -> set[Pid]:
        """
        Takes where (type Location) and returns the set of pids that match
        that location.
        Currently the only ones supported are:
            * others (all other proc)
            * this (only this proc)
            * <pid> (the pid of the proc)
        You can pass multiple locations using "+" as a separator like this:
            * "this+other" (all processes)
            * "123" (only the proc with pid=123)
            * "123+456" (only the procs with pids 123 and 456)
        """
        assert not self.dead, "IPC already closed"
        assert_type(where, Location, "where")
        locs:set[Pid] = set()
        for where in where.split("+"):
            if where == "others":
                all_pids:set[Pid] = {Pid(pid) for pid in self.get_all_pids()}
                locs.update(all_pids-{SELF_PID})
            elif where == "this":
                locs.add(SELF_PID)
            elif where.isdigit():
                locs.add(Pid(where))
            else:
                raise NotImplementedError(f"Invalid location={where!r} - " \
                                          f"read documentation")
        return locs

    def _got_event(self, event:Event) -> None:
        """
        If we got an event, execute the handler (if threaded) or put it in a
        queue for `call_queued_events` (if not threaded)
        """
        assert not self.dead, "IPC already closed"
        assert_type(event, Event, "event")
        non_threaded_handlers:list[Handler] = []
        # In threaded handlers, ignore the return value
        bindings:list = self._bindings.get(event.type, []) + \
                        self._bindings.get("", [])
        for (threaded,handler) in bindings:
            if handler is not None:
                if threaded:
                    Thread(target=handler, args=(event,), daemon=True).start()
                else:
                    non_threaded_handlers.append(handler)
        # Add non-threaded handlers to queue
        self._call_queue.append((non_threaded_handlers,event))

    def call_queued_events(self) -> None:
        """
        Call this method regularly if you called `.bind(threaded=False)`.
        It handles all of the handlers from the current thread.
        """
        assert not self.dead, "IPC already closed"
        while self._call_queue:
            handlers, event = self._call_queue.pop(0)
            for handler in handlers:
                ret:Break|None = handler(event)
                if ret:
                    break

    def get_all_pids(self) -> Iterable[str]:
        """
        Read all of the folders at the top of fs and assume any numbered
        folders are pids. If the pid doesn't exist, delete the folder.
        """
        assert not self.dead, "IPC already closed"
        for folder in self._fs.listdirs("."):
            if not folder.isdigit():
                continue
            if int(folder) != SELF_PID:
                if not pid_exists(int(folder)):
                    self._fs.removedir(folder)
                    continue
            yield folder

    def close(self) -> None:
        assert not self.dead, "IPC already closed"
        self.dead:bool = True
        # signal only works in main thread of the main interpreter
        # signal_register(self.sig, self._old_signal)
        self._fs.removedir(self._root)
        self._fs.close()

    def _check_got_data(self) -> None:
        assert not self.dead, "IPC already closed"
        # For each file in our folder:
        for filename in self._fs.listfiles(self._root):
            # Get the path and read it (we don't need to lock the fs for that)
            path:str = self._fs.join(self._root, filename)
            with self._fs.open(path, "rb", lock=False) as file:
                data:bytes = file.read()
            # If we read and decoded the data correctly, delete the file
            # Assume if we can decode data, it's the full data and we should
            # not expect anything to write to that file anyways
            try:
                event:Event = serialiser.enc_loads(data)
                assert_type(event, Event, "event")
            except (TypeError, ValueError, UnicodeDecodeError):
                continue
            self._fs.removefile(path)
            self._got_event(event)

    def _on_init(self) -> None:
        assert not self.dead, "IPC already closed"
        self._fs.makedir(self._root)

    def _add_listener(self, event:EventType) -> None:
        assert not self.dead, "IPC already closed"
        if self._bound: return None
        self._bound:bool = True
        # Get old signal so we can reset it at cleanup
        self._old_signal = signal_get(self.sig)
        # Signals shouldn't really do anything complicated or time consuming
        # as another signal can come in at any time causing a RecursionError
        event:_Event = _Event()
        def inner(*args:tuple) -> None:
            # Event.set must run in a new thread otherwise it somehow
            # causes a RecursionError in event.wait. Absolutely no clue why
            Thread(target=event.set, daemon=True).start()
        def threaded() -> None:
            while not self.dead:
                event.wait()
                event.clear()
                if not self.dead:
                    self._check_got_data()
        signal_register(self.sig, inner)
        Thread(target=threaded, daemon=True).start()

    def _send_data(self, pid:Pid, data:bytes, *, timeout:int=1000) -> None:
        assert not self.dead, "IPC already closed"
        # Timeout is in milliseconds
        attempts:int = 100
        for i in range(attempts):
            try:
                file:File = self._fs.get_free_file(str(pid), "%d%d.msg", "wb")
            except FileNotFoundError:
                return None # pid must have not created a folder/died
            if file is not None:
                break
            sleep(timeout/1000/attempts)
        else:
            raise FileExistsError("Too many messages left to pid but none " \
                                  "of them are read")
        with file:
            file.write(data)
        signal_send(pid, self.sig)


def assert_type(obj:T|object, T:type, what:str=None) -> None:
    if T is None:
        if obj is None:
            return None
        type_name:str = "NoneType"
    elif T == Callable:
        if callable(obj):
            return None
        type_name:str = "Callable"
    else:
        if not isinstance(T, type):
            raise ValueError(f"T must be a type variable not " \
                             f"{T.__class__.__name__}")
        if isinstance(obj, T):
            return None
        type_name:str = T.__name__
    if what is None:
        raise TypeError(f"expected type {type_name} not " \
                        f"{obj.__class__.__name__}")
    else:
        raise TypeError(f"expected {what!r} to be a {type_name} object not " \
                        f"a {obj.__class__.__name__} object")


if __name__ == "__main__":
    ipc:BaseIPC = IPC("program_name", sig=SIGUSR1)
    ipc.bind("focus", lambda e: print("@", e), threaded=True)
    ipc.event_generate("focus", where="others")