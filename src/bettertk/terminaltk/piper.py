from __future__ import annotations
from tempfile import TemporaryDirectory
import os


READ:int = os.O_RDONLY
WRITE:int = os.O_WRONLY
CLOSED:int = (READ|WRITE) << 2


class Pipe:
    __slots__ = "owns", "opened", "mode", "path", "fd"

    def __init__(self, path:str, mode:int, *, owns:bool=True) -> Pipe:
        assert mode in (READ, WRITE), "Invalid mode."
        self.owns:bool = owns and (mode == WRITE)
        self.opened:bool = False
        self.mode:int = mode
        self.path:str = path
        self.fd:int = None

    def start(self) -> None:
        assert not self.opened, "Pipe already open"
        assert self.mode != CLOSED, "Closed pipes are dead pipes"
        self.fd:int = os.open(self.path, self.mode)
        self.opened:bool = True

    def read(self, length:int) -> bytes:
        if not self.opened: return b""
        assert self.mode == READ, "Pipe isn't in os.O_RDONLY mode"
        return os.read(self.fd, length)

    def write(self, data:bytes) -> Success:
        assert self.opened, "Pipe isn't open"
        assert self.mode == WRITE, "Pipe isn't in os.O_WRONLY mode"
        try:
            os.write(self.fd, data)
            return True
        except BrokenPipeError:
            return False

    def close(self) -> None:
        assert self.opened, "Pipe isn't open"
        self.opened:bool = False
        self.mode:int = CLOSED
        os.close(self.fd)
        if self.owns:
            os.unlink(self.path)


class PipePair:
    __slots__ = "self2other", "other2self", "debug_log"
    taken_idxs:int = -1

    def __init__(self, self2other:str, other2self:str, *, owns:bool=True):
        self.debug_log:list[str] = []
        if owns:
            os.mkfifo(self2other)
            os.mkfifo(other2self)
        self.self2other:Pipe = Pipe(self2other, WRITE, owns=owns)
        self.other2self:Pipe = Pipe(other2self, READ, owns=owns)

    def start(self) -> None:
        if self.self2other.owns: # master
            self.self2other.start()
            self.other2self.start()
        else: # slave
            self.other2self.start()
            self.self2other.start()

    def close(self) -> None:
        self.self2other.close()
        self.other2self.close()
        self.debug_log.append(f"Closed")

    def write(self, data:bytes) -> None:
        self.self2other.write(data)
        self.debug_log.append(f"Wrote: {data!r}")

    def read(self, length:int) -> bytes:
        data:bytes = self.other2self.read(length)
        self.debug_log.append(f"Read: {data!r}")
        return data

    def dump_log(self) -> str:
        return "PipeLog:\n\t" + "\n\t".join(self.debug_log)

    def reverse(self) -> tuple[str,str]:
        return self.other2self.path, self.self2other.path

    @classmethod
    def from_path(Class:type, path:str) -> PipePair:
        return PipePair(PipePair.create_pipe(path), PipePair.create_pipe(path))

    @staticmethod
    def create_pipe(path:str) -> str:
        idx:int = PipePair.taken_idxs+1
        while os.path.exists(os.path.join(path, str(idx))):
            idx += 1
        PipePair.taken_idxs:int = idx
        filepath:str = os.path.join(path, str(idx))
        return filepath


class TmpPipePair(PipePair):
    __slots__ = ("tmp",)

    def __init__(self, self2other:str, other2self:str, tmp, *, owns:bool=True):
        super().__init__(self2other, other2self, owns=owns)
        self.tmp:TemporaryDirectory = tmp

    @classmethod
    def from_tmp(Class:type) -> TmpPipePair:
        tmp:TemporaryDirectory = TemporaryDirectory()
        self2other:str = PipePair.create_pipe(tmp.name)
        other2self:str = PipePair.create_pipe(tmp.name)
        return TmpPipePair(self2other, other2self, tmp, owns=True)

    def close(self) -> None:
        super().close()
        self.tmp.cleanup()