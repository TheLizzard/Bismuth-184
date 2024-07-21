from __future__ import annotations


TEST:bool = False
LOG:bool = False
log:list = []


def sign(x:int) -> int:
    if x < 0:
        return -1
    if x > 0:
        return +1
    if x == 0:
        return 0


class Idx:
    __slots__ = "value", "dirty", "deleted"
    singletons:dict[int:Idx] = dict()

    def __new__(Cls:type, new_value:int) -> Idx:
        if new_value in Idx.singletons:
            if LOG:
                log.append(("Idx.__new__", new_value, "cache"))
            return Idx.singletons[new_value]
        self:Idx = super().__new__(Cls)
        Idx.singletons[new_value] = self
        self.deleted:bool = False
        self.dirty:bool = True
        if LOG:
            log.append(("Idx.__new__", new_value))
        return self

    def __repr__(self) -> str:
        dirty:str = "|d" if self.dirty else ""
        return f"Idx[{self.get()}{dirty}]"

    def get(self) -> int:
        return self.value

    def set(self, new_value:int) -> None:
        if LOG:
            log.append(("Idx.set", self.value, new_value))
        assert not self.deleted, "Don't destroy and call this function"
        assert new_value not in Idx.singletons, "KeyAlreadyExists"
        Idx.singletons[new_value] = Idx.singletons.pop(self.value)
        self._set(new_value)
        self.dirty:int = True

    def _set(self, new_value:int) -> None:
        if LOG:
            log.append(("Idx._set", self.value, new_value))
        self.value:int = new_value

    def destroy(self) -> None:
        if LOG:
            log.append(("Idx.destroy", self.value))
        assert not self.deleted, "Idx already destroyed"
        self.deleted:bool = True
        sself:Idx = self.singletons.pop(self.value)

    def undestroy(self) -> None:
        if LOG:
            log.append(("Idx.undestroy", self.value))
        assert self.deleted, "Idx not destroyed"
        assert self.value not in self.singletons, "Idx in singletons"
        self.deleted:bool = False
        self.singletons[self.value] = self

    def moveup(self, delta:int) -> None:
        if LOG:
            log.append(("Idx.moveup", self.value, delta))
        self.destroy()
        if delta < 0:
            iterator:Iterator[int] = range(self.value+1, self.value-delta+1)
        else:
            iterator:Iterator[int] = range(self.value-1, self.value-delta-1, -1)
        # iterator=tuple(iterator);print(iterator, delta)
        for i in iterator:
            Idx.singletons[i].set(i+1*sign(delta))
        self._set(self.value-delta)
        self.dirty:bool = True
        self.undestroy()

    def __eq__(self, other:Idx) -> bool:
        assert isinstance(other, Idx), "TypeError"
        return self.value == other.value

    def __leq__(self, other:Idx) -> bool:
        assert isinstance(other, Idx), "TypeError"
        return self.value <= other.value

    def __geq__(self, other:Idx) -> bool:
        assert isinstance(other, Idx), "TypeError"
        return self.value >= other.value

    def __lt__(self, other:Idx) -> bool:
        assert isinstance(other, Idx), "TypeError"
        return self.value < other.value

    def __gt__(self, other:Idx) -> bool:
        assert isinstance(other, Idx), "TypeError"
        return self.value > other.value

    __init__ = _set
    __hash__ = get


class IdxGiver:
    __slots__ = "items", "item2idx", "max_idx", "Item"

    def __init__(self, Item:type) -> IdxGiver:
        self.item2idx:dict[Item:Idx] = dict()
        self.items:list[Item] = []
        self.Item:type = Item
        self.max_idx:int = 0

    def __repr__(self) -> str:
        inners:tuple[Item,Idx] = self.item2idx.items()
        second = lambda x: x[1]
        inners:tuple[Item,Idx] = sorted(inners, key=second)
        inner:str = " ".join(f"{item}:{idx}" for item,idx in inners)
        return f"IdxGiver({inner})"

    def __getitem__(self, key:Item|Idx) -> Idx|Item:
        assert isinstance(key, self.Item|Idx), "TypeError"
        if isinstance(key, self.Item):
            return self.item2idx[key]
        elif isinstance(key, Idx):
            return self.items[key.value]
        else:
            raise NotImplementedError("Unreachable code")

    def push_item(self, item:Item) -> Idx:
        assert isinstance(item, self.Item), "TypeError"
        assert item not in self.item2idx, "Item already added"
        idx, self.max_idx = Idx(self.max_idx), self.max_idx+1
        self.items.append(item)
        self.item2idx[item] = idx
        if LOG:
            log.append(("IGiver.push_item", item, idx))
        if TEST: self.sanity_check()
        return idx

    def remove_item(self, item:Item) -> None:
        assert isinstance(item, self.Item), "TypeError"
        assert item in self.item2idx, "Item doesn't exist"
        idx:Idx = self.item2idx.pop(item)
        idx.destroy()
        _idx:int = idx.value
        if TEST: assert 0 <= _idx < len(self.items), "Idx out of range"
        # Fix items
        self.items.pop(_idx)
        # Fix idx2item
        for _i in range(_idx+1, self.max_idx):
            Idx(_i).set(_i-1)
        self.max_idx -= 1
        if LOG:
            log.append(("IGiver.remove_item", item, idx))
        if TEST: self.sanity_check()

    def moveup(self, item:Item, delta:int) -> None:
        if delta == 0: return None
        idx:Idx = self.item2idx[item]
        assert 0 <= idx.value-delta < len(self.items), "Illegal move"
        # Fix items
        self.items.insert(idx.value-delta, self.items.pop(idx.value))
        # Fix idx2item
        idx.moveup(delta)
        if LOG:
            log.append(("IGiver.moveup", item, idx, delta))
        if TEST: self.sanity_check()

    def sanity_check(self) -> None:
        assert len(self.item2idx) == len(self.items), "SanityCheck"
        for idx in self.idxs:
            item:Item = self.items[idx.value]
            assert idx == self.item2idx[item], "SanityCheck"

    @property
    def idxs(self) -> Iterable[Idx]:
        yield from map(Idx, range(len(self.items)))