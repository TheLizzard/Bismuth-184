from __future__ import annotations
from itertools import repeat, filterfalse
from random import shuffle, seed, randint
import shutil
import stat
import os
seed(42)

try:
    from .idxgiver import Idx, IdxGiver
except ImportError:
    from idxgiver import Idx, IdxGiver


KNOWN_EXT:tuple[str] = ("cpp", "file", "py", "txt", "h", "c++", "java")
NEW_ITEM_NAME:str = "a-placeholder-name-21544329271124491949"
SPACES_PER_INDENTATION:int = 8 # cli only
DEBUG:bool = False
TEST:bool = False
WARNINGS:bool = True

MAX_ITEMS_IN_DIR:int = float("inf") # 40
MAX_ITEMS_TAKES:int = 5
MAX_ITEMS_ITENT:str = "..."
assert MAX_ITEMS_TAKES <= MAX_ITEMS_IN_DIR, "Make sure this assertion holds"


FILTER_FALSE_FILES   = [
                         NEW_ITEM_NAME.__eq__,
                         # python/rpython
                         lambda s:s.endswith(".pyo"),
                         lambda s:s.endswith(".pyc"),
                         # git/github
                         "LICENSE".__eq__,
                       ]
FILTER_FALSE_FOLDERS = [
                         NEW_ITEM_NAME.__eq__,
                         # python/rpython
                         "__pycache__".__eq__,
                         # git/github
                         ".git".__eq__,
                       ]


def isfolder(item:Item, followsym:bool=False) -> bool:
    return isinstance(item, Folder)

def isfile(item:Item) -> bool:
    return isinstance(item, File)

def first(iterable:Iterable[T]) -> T:
    return next(iter(iterable))


class Error:
    __slots__ = ("error",)

    def __init__(self, error:str|None=None) -> Error:
        assert isinstance(error, str|None), "TypeError"
        self.error:str = error

    def __bool__(self) -> bool:
        return (self.error is not None)

    def __repr__(self) -> str:
        if self.error is None:
            return f"NoError"
        else:
            return f'Error("{self.error}")'


class FileSystem:
    @staticmethod
    def is_untouchable(path:str) -> bool:
        return path.rstrip("/").endswith(MAX_ITEMS_ITENT)

    def rename(self, fullpath:str, newname:str) -> Error:
        if newname in (MAX_ITEMS_ITENT, NEW_ITEM_NAME):
            return Error("Reserved filename")
        return self.move(fullpath, self.join(self.dirname(fullpath), newname))

    def move(self, source:str, destination:str) -> Error:
        if self.is_untouchable(source) or self.is_untouchable(destination):
            return Error("Source/destination is untouchable")
        if not self.exists(source):
            return Error("Source doesn't exist")
        if self.exists(destination):
            return Error("Newpath already exists")
        shutil.move(source, destination)
        return Error()

    def _delete(self, path:str) -> None:
        if self.isfile(path) or self.islink(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)

    def delete(self, path:str, force:bool=False) -> Error:
        if self.is_untouchable(path):
            return Error("Path is untouchable")
        assert TEST or (not force), "Force only works with TEST"
        if not force:
            if input(f'Delete "{path}"? [y/n]:').lower() != "y":
                return Error("Canceled by user")
        self._delete(self.abspath(path))
        return Error()

    def clean(self, path:str, *, force:bool=False) -> Error:
        """
        Deletes everything inside the path but leaves path untouched.
        """
        if self.is_untouchable(path):
            return Error("Path is untouchable")
        assert TEST and force, "Program this if needed"
        root:str = self.abspath(path)
        files_folders, error = self.listdir(root)
        if not error:
            for filename, _ in files_folders:
                self._delete(self.join(root, filename))
        return error

    def makedirs(self, path:str) -> Error:
        if self.is_untouchable(path):
            return Error("Path is untouchable")
        os.makedirs(path, exist_ok=True)
        return Error()

    def newfolder(self, path:str) -> Error:
        if self.is_untouchable(path):
            return Error("Path is untouchable")
        try:
            os.mkdir(path)
            if not os.path.exists(path):
                raise NotADirectoryError()
        except FileExistsError:
            return Error(f'FileExistsError("{path}")')
        except NotADirectoryError:
            return Error(f'IllegalCharactersError("{path}")')
        return Error()

    def newfile(self, path:str) -> Error:
        if self.is_untouchable(path):
            return Error("Path is untouchable")
        if self.isfolder(path):
            return Error("IsADirectoryError")
        if self.exists(path):
            return Error("Path already exists.")
        try:
            with open(path, "w") as file: ...
        except Exception as error:
            return Error(f"Couldn't create file because: {error.__class__}")
        return Error()

    def chdir(self, path:str) -> Error:
        if self.is_untouchable(path):
            return Error("Path is untouchable")
        if not self.exists(path):
            return Error("Path doesn't exist.")
        os.chdir(path)
        return Error()

    def listdir(self, path:str) -> tuple[tuple[str,str], Error]:
        if self.is_untouchable(path):
            return (), Error("Path is untouchable")
        try:
            islink = lambda x: os.path.islink(os.path.join(path, x))
            try:
                root, folders, files = next(os.walk(path))
            except StopIteration:
                root, folders, files = path, (), ()
            # Bound the number of files/folders:
            if len(files) > MAX_ITEMS_IN_DIR:
                files:tuple[str] = self.bound_listdir(files)
            if len(folders) > MAX_ITEMS_IN_DIR:
                folders:tuple[str] = self.bound_listdir(folders)
            # Skip links:
            files:tuple[str] = filterfalse(islink, files)
            folders:tuple[str] = filterfalse(islink, folders)
            # Other filters:
            for filterer in FILTER_FALSE_FILES:
                files:tuple[str] = filterfalse(filterer, files)
            for filterer in FILTER_FALSE_FOLDERS:
                folders:tuple[str] = filterfalse(filterer, folders)
            return tuple(zip(sorted(folders), repeat("folder"))) + \
                   tuple(zip(sorted(files), repeat("file"))), Error()
        except PermissionError:
            return (), Error("PermissionError")

    @staticmethod
    def bound_listdir(data:tuple[str]) -> tuple[str]:
        data:list[str] = sorted(data)
        data:list[str] = data[:MAX_ITEMS_TAKES] + [MAX_ITEMS_ITENT]
        return tuple(data)

    def access(self, path:str) -> tuple[bool,bool,bool]:
        if self.is_untouchable(path):
            return False, False, False
        try:
            st:int = os.stat(path).st_mode
            read:bool = st & (stat.S_IRGRP|stat.S_IRUSR)
            write:bool = st & (stat.S_IWGRP|stat.S_IWUSR)
            exec:bool = st & (stat.S_IXGRP|stat.S_IXUSR)
        except OSError:
            read = write = exec = 0
        return bool(read), bool(write), bool(exec)

    def exists(self, path:str) -> bool:
        if self.is_untouchable(path):
            return False
        return os.path.exists(path)

    def abspath(self, path:str) -> str:
        return os.path.abspath(path)

    def join(self, *paths:tuple[str]) -> str:
        return os.path.join(*paths)

    def dirname(self, path:str) -> str:
        return os.path.dirname(path)

    def filename(self, path:str) -> str:
        return os.path.split(path)[-1]

    def isfile(self, path:str) -> bool:
        return os.path.isfile(path)

    def isfolder(self, path:str) -> bool:
        return os.path.isdir(path)

    def islink(self, path:str) -> bool:
        return os.path.islink(path)


class ProvidedFileSystem(FileSystem):
    def __init__(self, files_folders):
        self.files_folders:list[tuple[str,str]] = list(files_folders)
        shuffle(self.files_folders)
    def move(self, oldpath:str, newpath:str) -> Error:
        return Error()
    def delete(self, fullpath:str) -> Error:
        return Error()
    def newfolder(self, fullpath:str, name:str) -> Error:
        return Error()
    def newfile(self, fullpath:str, name:str) -> Error:
        return Error()
    def listdir(self, path:str) -> tuple[tuple[str, str], Error]:
        output:tuple[str, str] = []
        for name, type in self.files_folders:
            if name.startswith(path+"/"):
                relpath:str = name[len(path)+1:]
                if "/" not in relpath:
                    output.append((relpath, type))
        return output, Error()
    def access(self, path:str) -> tuple[bool, bool, bool]:
        return (True, True, True)


class Item:
    __slots__ = "master", "name", "indentation", "idx", "root", "perms"

    def __init__(self, name:str, root:Root, master:Item=None) -> Item:
        assert isinstance(master, Item|None), "TypeError"
        assert isinstance(root, Root), "TypeError"
        assert isinstance(name, str|None), "TypeError"
        if name is None:
            assert master is None, "ValueError"
        self.master:Item = master
        self.indentation:int = 0
        self.root:Root = root
        self.name:str = name
        self.idx:Idx = None
        self.perms:int = 0
        if (name is not None) and (name != NEW_ITEM_NAME):
            self.update_perms()

    def update_perms(self) -> None:
        r, w, x = self.root.filesystem.access(self.fullpath)
        self.perms:int = (x<<2) | (w<<1) | r

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.name})"

    @property
    def fullpath(self) -> str:
        return self.root.filesystem.join(self.master.fullpath, self.name)

    @property
    def purename(self) -> str:
        assert self.master is not None, "Root doesn't have a purename"
        if self.master.master is None:
            return self.root.filesystem.filename(self.name)
        if self.name == NEW_ITEM_NAME:
            return ""
        return self.name

    def fix_indentation(self) -> None:
        """
        Fix my + my children's indentation flags.
        """
        self.indentation:int = 0
        withself:bool = self.master is not None
        for item, shown in self.recurse_children(withself=withself):
            item.indentation:int = item.master.indentation + 1

    def recurse_children(self, *, withself:bool, only_shown:bool=False) \
                                                  -> Iterator[tuple[Item,bool]]:
        """
        Return all of my children recursively with shown flags. The flag
          tells you if the corresponding item should be shown or not.
        NOTE: It assumes that "self" is shown.
        """
        shown_top:bool = True
        stack:list[tuple[Item,bool]] = [(self, shown_top)]
        while len(stack) > 0:
            item, shown = stack.pop()
            if only_shown and (not shown):
                continue
            if isfolder(item, followsym=False):
                stack.extend(zip(reversed(self.sorted(item.children)),
                                 repeat(item.expanded & shown)))
            if (item is self) and (not withself):
                continue
            yield item, shown

    def move(self, target:Folder, apply_filesystem:bool=True) -> Error:
        """
        Move self to another folder
        """
        if target.name == NEW_ITEM_NAME:
            return Error("Placeholder name not allowed")
        if self.name == NEW_ITEM_NAME:
            return Error("Placeholder name not allowed")
        if isfile(target):
            return Error("Target must be a folder.")
        if self.master is None:
            return Error("Don't even try to move/delete/rename the base root.")
        if self.master.master is None:
            return Error("Can't move roots")
        if target.master is None:
            return Error("Can't move to virtual root")
        if self.master == target:
            return Error("Nop???") # Can cause bugs. DO NOT ALLOW
        if (target.fullpath+"/").startswith(self.fullpath+"/"):
            return Error("Can't move folder inside itself")

        oldpath, oldmaster = self.fullpath, self.master
        newpath:str = self.root.filesystem.join(target.fullpath, self.name)
        if apply_filesystem:
            error:Error = self.root.filesystem.move(oldpath, newpath)
            if error:
                if WARNINGS: print(f"[WARNING]: Handled error in move: {error}")
                return error

        assert self in self.master.children, "SanityCheck"
        assert self not in target.children, "SanityCheck"
        self.master.children.remove(self)
        target.children.append(self)
        self.master:Item = target
        self.fix_indentation() # Fix indentation
        self.correct_idx() # Fix idxs
        assert self.fullpath == newpath, "SanityCheck" # fullpath is correct
        if DEBUG: print(f"[DEBUG]: Moved {self} => {target}")
        return Error()

    def rename(self, newname:str) -> Error:
        """
        Rename self
        If we have a placeholder name, then we automatically get touched.
        """
        if newname == self.name:
            return Error("Same name rename")
        if newname == NEW_ITEM_NAME:
            return Error("Placeholder name not allowed")
        if self.master is None:
            return Error("Don't even try to move/delete/rename the base root")
        if self.master.master is None:
            parent_name:str = self.root.filesystem.dirname(self.name)
            new_name:str = self.root.filesystem.join(parent_name, newname)
        # Now new_name is just a name with no "/"s
        is_new:bool = (self.name == NEW_ITEM_NAME)
        if newname in tuple(item.name for item in self.master.children):
            return Error("Name already exists")
        if is_new:
            if DEBUG: print(f"[DEBUG]: Touching {self}")
            error:Error = self.touch(newname)
            if error:
                if WARNINGS: print(f"[WARNING]: Handled touch error in rename: {error}")
                return error
        else:
            error:Error = self.root.filesystem.rename(self.fullpath, newname)
            if error:
                if WARNINGS: print(f"[WARNING]: Handled error in rename: {error}")
                return error
            if DEBUG: print(f'[DEBUG]: Renamed "{self.name}" => "{newname}"')
            self.name:str = newname
        self.correct_idx() # Fix idxs
        return Error()

    def delete(self, *, apply_filesystem:bool=True) -> Error:
        """
        Deletes self and self.children recursively
        """
        if self.name == NEW_ITEM_NAME:
            if apply_filesystem:
                return Error("Placeholder name not allowed")
        if self.master is None:
            return Error("Don't even try to move/delete/rename the base root")
        if apply_filesystem:
            error:Error = self.root.filesystem.delete(self.fullpath)
            if error:
                if WARNINGS: print(f"[WARNING]: Handled error in delete: {error}")
                return error
        self.master.children.remove(self)
        for item, shown in self.recurse_children(withself=True):
            self.root.igiver.remove_item(item)
            if DEBUG: print(f"[DEBUG]: Mark deleted {item}")
        return Error()

    def touch(self, name:str) -> Error:
        assert self.name == NEW_ITEM_NAME, "Please don't rename me first."
        self.name:str = name
        if isfile(self):
            error:Error = self.root.filesystem.newfile(self.fullpath)
        elif isfolder(self):
            error:Error = self.root.filesystem.newfolder(self.fullpath)
        else:
            raise NotImplementedError("self not file nor folder.")
        if error:
            # Undo the `self.name:str = name`
            self.name:str = NEW_ITEM_NAME
            return error
        self.update_perms()
        self.correct_idx() # Fix idxs
        return Error()

    def correct_idx(self) -> None:
        assert self.master is not None, "Root(None) has no idx"
        # Even if self.idx hasn't changed, indentation might have changed
        self.idx.dirty:bool = True
        # If we are root's children, don't reorder us
        if self.master.master is None:
            return None
        _newidx:int = self.master.get_idx_insert(self)
        if self.idx.value == _newidx:
            return None
        if self.idx.value < _newidx:
            correction:int = self.get_idx_size()
            _newidx -= correction
            if DEBUG: print(f"[DEBUG]: {self.idx}-[{correction=}]")
        # Calculate delta
        delta:int = self.idx.value - _newidx
        if delta == 0:
            return
        # Apply delta to all objects
        children = list(self.recurse_children(withself=True))
        if delta < 0:
            children:list[tuple[Item,bool]] = reversed(children)
        for subitem, shown in children:
            self.root.igiver.moveup(subitem, delta)
            if DEBUG: print(f"[DEBUG]: Moving {subitem} {delta=}")
        assert self.idx.value == _newidx, "SanityCheck"

    def get_idx_size(self) -> int:
        """
        Returns the size of self. Must be 1 if isfile. Must be >=1 if isfolder.
        """
        raise NotImplementedError("Override this method")

    def update(self, fullsync:bool=False) -> None:
        """
        Look at filesystem for any changes to self
        """
        raise NotImplementedError("Override this method")


class Folder(Item):
    __slots__ = "_expanded", "children"

    def __init__(self, name, root:Root, master:Item):
        super().__init__(name, root=root, master=master)
        self._expanded:bool = root.autoexpand
        self.children:list[Item] = []
        if self.master is None:
            self.fix_indentation()

    def update(self, fullsync:bool=False) -> None:
        """
        Updates `self.children` with a new list with the new files/folders.
        """
        assert not fullsync, "Don't use this"
        # If we don't have the perms:
        if not (self.perms & 1):
            return None
        # If we haven't expanded, don't update
        if not self.expanded:
            return None
        current_children = tuple(self.children)
        files_folders, error = self.root.filesystem.listdir(self.fullpath)
        assert not error, "InternalError" # "Perms changed for some reason"
        for itemname, type in files_folders:
            assert itemname != NEW_ITEM_NAME, "An item is using a reserved name"
            item:Item|None = self.get_item_from_name(itemname)
            if item is not None:
                not_unchanged:bool = (isfile(item)   and (type == "file")) or \
                                     (isfolder(item) and (type == "folder"))
                if not_unchanged:
                    item.update(fullsync)
                    continue
                item.delete(apply_filesystem=False)
            if type == "file":
                item:File = File(itemname, master=self, root=self.root)
            elif type == "folder":
                item:Folder = Folder(itemname, master=self, root=self.root)
            else:
                raise NotImplementedError("Invalid filesystem object type")
            self.add_item(item)
            if isfolder(item):
                item.update(fullsync)

        for child in self.children.copy():
            if child.name not in map(first, files_folders):
                if (child.name == NEW_ITEM_NAME) and (not fullsync):
                    continue
                child.delete(apply_filesystem=False)

    @property
    def expanded(self) -> bool:
        return self._expanded

    @expanded.setter
    def expanded(self, value:bool) -> None:
        assert isinstance(value, bool), "TypeError"
        self._expanded, old_expanded = value, self._expanded
        if (not old_expanded) and self._expanded:
            self.update()

    def get_item_from_name(self, name:str) -> Item|None:
        """
        Gets the item from self.children given a name.
        """
        for item in self.children:
            if item.name == name:
                return item
        return None

    def to_string(self) -> str:
        assert TEST, "This can only be used in TEST mode."
        output:str = ""
        for item in self.sorted(self.children):
            indentation:str = " "*SPACES_PER_INDENTATION*(item.indentation-1)
            r:str = "r" if item.perms&1 else " "
            w:str = "w" if item.perms&2 else " "
            flags:str = f"({item.idx.value}{r}{w})"
            if isfile(item):
                output += f"{indentation}{item.name}{flags}\n"
            # If it's a folder show it then show it's contents
            elif isfolder(item):
                symbol:str = "-" if item.expanded else "+"
                output += f"{indentation}{symbol}{item.name}{flags}\n"
                output += item.to_string() + "\n"
            else:
                raise NotImplementedError(f'No idea what this: "{item}" is')
        return output.replace("\n\n", "\n")[:-1]

    def __call__(self) -> None:
        assert TEST, "This can only be used in TEST mode."
        print(self.to_string())

    def add_item(self, item:Item) -> None:
        """
        Adds an item as a child.
        """
        if DEBUG:
            m = self
            while m.master is not None:
                m = m.master
            if TEST:
                print(m.to_string() + "\n" + "="*80)
            print(f"[DEBUG]: Trying to add {item} to {self}")
        assert isinstance(item, Item), "TypeError"
        item.idx:Idx = self.root.igiver.push_item(item)
        if DEBUG: print(f"[DEBUG]: Current idx for {item} is {item.idx}")
        # item.idx:Idx = self.root.igiver[item]
        self.children.append(item)
        item.master:Item = self
        item.fix_indentation()
        item.correct_idx() # Fix idxs
        if DEBUG: print(f"[DEBUG]: Added {item} to {self} at {item.idx}")
        return item

    def get_idx_insert(self, item:Item, ignore_item:bool=False) -> int:
        children:list[Item] = self.sorted(self.children.copy())
        if item in children:
        #if ignore_item:
        #    assert item in children, "ignore_item=True when item isn't in self"
            children.remove(item)
        assert item not in children, "InternalError"
        for loc, child in enumerate(children):
            if self._get_idx_insert_compare(child, item): # child > item
                return child.idx.value
        # Base base, empty folder
        if len(children) == 0:
            if DEBUG: print(self, self.idx)
            return self.idx.value+1
        # If item should be at the end:
        child:Item = children[-1]
        while isfolder(child):
            if len(child.children) == 0:
                break
            child:Item = self.sorted(child.children)[-1]
        return child.idx.value+1

    @staticmethod
    def _get_idx_insert_compare(itema:Item, itemb:Item) -> bool:
        if DEBUG: print(f"[DEBUG]: Compare {itema}>?{itemb}", end="")
        # returns True iff itema > itemb
        if isfile(itema) and isfolder(itemb):
            if DEBUG: print(" => True")
            return True
        if isfolder(itema) and isfile(itemb):
            if DEBUG: print(" => False")
            return False
        if itemb.name == NEW_ITEM_NAME:
            if DEBUG: print(" => False")
            return False
        if itema.name == NEW_ITEM_NAME:
            if DEBUG: print(" => True")
            return True
        if itemb.name == MAX_ITEMS_ITENT:
            if DEBUG: print(" => False")
            return False
        if itema.name == MAX_ITEMS_ITENT:
            if DEBUG: print(" => True")
            return True
        if DEBUG: print(f" => t{itema.name > itemb.name}")
        return itema.name >= itemb.name

    @staticmethod
    def sorted(children:list[Item]) -> list[Item]:
        return sorted(children, key=lambda item: item.idx)

    def newfolder(self, name:str=NEW_ITEM_NAME) -> Folder:
        assert self.master is not None, "Master can't be None"
        names:Iterator[str] = map(lambda i: i.name, self.children)
        assert NEW_ITEM_NAME not in tuple(names), "Name already taken"
        folder:Folder = Folder(name=NEW_ITEM_NAME, master=self, root=self.root)
        self.add_item(folder)
        return folder

    def newfile(self) -> File:
        assert self.master is not None, "Master can't be None"
        names:Iterator[str] = map(lambda i: i.name, self.children)
        assert NEW_ITEM_NAME not in tuple(names), "Name already taken"
        file:File = File(name=NEW_ITEM_NAME, master=self, root=self.root)
        self.add_item(file)
        return file

    def get_idx_size(self) -> int:
        count:int = 0
        items:list[Item] = [self]
        while len(items) > 0:
            count += 1
            item:Item = items.pop()
            if isfolder(item):
                items.extend(item.children)
        return count


class File(Item):
    __slots__ = ()

    def __init__(self, name:str, root:Root, master:Item) -> File:
        super().__init__(name, root=root, master=master)

    def update(self, fullsync:bool=False) -> None:
        assert not fullsync, "Don't use this"

    def get_idx_size(self) -> int:
        return 1


class Root(Folder):
    __slots__ = "igiver", "filesystem", "autoexpand"

    def __init__(self, filesystem:FileSystem, autoexpand:bool=True):
        self.autoexpand:bool = autoexpand
        self.igiver:IdxGiver = IdxGiver(Item)
        self.filesystem:FileSystem = filesystem
        super().__init__(name=None, root=self, master=None)
        self.idx:Idx = self.igiver.push_item(self)
        self._expanded:bool = True

    @property
    def fullpath(self) -> str:
        return ""

    def add(self, path:str) -> Folder|None:
        """
        Adds a folder to the list of folders to be displayed. Please
        note that the input must be a folder otherwise this returns `None`
        """
        fullpath:str = self.filesystem.abspath(path)
        if not os.path.exists(fullpath):
            return None
        if not os.path.isdir(fullpath):
            return None
        folder:Folder = Folder(fullpath, root=self.root, master=self)
        super().add_item(folder)
        folder.update()
        return folder

    def remove(self, item_or_path:Item|str) -> None:
        """
        Removes a folder that was added using the `.add` method.
        Raises `ValueError`, if the folder isn't in `self.children`
        """
        if isinstance(item_or_path, Item):
            assert item_or_path in self.children, "Item not in Root"
            item_or_path.delete(apply_filesystem=False)
        else:
            fullpath:str = self.filesystem.abspath(item_or_path)
            for child in self.children:
                if child.name == fullpath:
                    child.delete(apply_filesystem=False)
                    return None
            raise ValueError("Can't remove that folder because it " \
                             "wasn't added.")

    def update(self, fullsync:bool=False) -> None:
        """
        Update the tree.
        """
        assert not fullsync, "Don't use this"
        for child in self.children:
            child.update(fullsync=fullsync)

    def get_item_from_path(self, path:str) -> Item:
        assert TEST, "This can only be used in TEST mode."
        orig_path:str = path
        parent:Item = self
        while path != "":
            for child in parent.children:
                if path.startswith(child.name):
                    path:str = path.replace(child.name, "", 1).lstrip("/")
                    parent:Item = child
                    break
            else:
                raise ValueError(f"Not in self... {orig_path}")
        assert child.fullpath == orig_path.rstrip("/"), "InternalError"
        return child

    def idx_to_item(self, idx:Idx|int) -> Item:
        if isinstance(idx, int):
            idx:Idx = Idx(idx)
        assert isinstance(idx, Idx), "TypeError"
        return self.igiver[idx]


if __name__ == "__main__":
    TEST = True
    number_of_tests = 1

    files_folders:tuple[str,str] = (
                                     ("/test", "folder"),
                                     ("/test/f", "file"),
                                   )
    for name,_ in files_folders: assert not name.endswith("/"), "Error in test"

    # filesystem = ProvidedFileSystem(files_folders)
    filesystem = FileSystem()
    explorer = Root(filesystem)
    # explorer.add("/test")
    # explorer.add("/media/thelizzard/C36D-8837")
    explorer.add(".")
    DEBUG = True
    explorer()
    target = explorer.get_item_from_path("/test/f")
    e = target.rename("")
    print(e)
    explorer()
