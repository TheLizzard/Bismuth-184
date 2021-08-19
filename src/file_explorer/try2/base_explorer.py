import os


MAX_FILES_PER_FOLDER = 10
SHOW_MAX_FILES_PER_FOLDER = 0
KNOWN_EXT = ("cpp", "file", "py", "txt")


class Item:
    def __init__(self, name:str, master=None):
        self.master = master
        self.name = name
        self.garbage_collect = False
        self.new = True
        if master is not None:
            self.full_path = master.full_path + "/" + name

        if self.master is None:
            self.indentation = 0
        else:
            self.indentation = self.master.indentation + 1

    def destroy(self) -> None:
        if not self.garbage_collect:
            self.master.children.remove(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def _update(self) -> None:
        return None

    def move_to(self, target) -> None:
        if target.isfile:
            raise ValueError("Target must be a folder not file.")
        self.master.children.remove(self)
        self.master = target
        target.children.append(self)
        target.sort_children()
        self.fix_indentation()

    def fix_indentation(self) -> None:
        fix_indentation_list = [self]
        while len(fix_indentation_list) != 0:
            item = fix_indentation_list.pop(0)
            if not item.isfile:
                fix_indentation_list.extend(item.children)
            item.indentation = item.master.indentation + 1

    def sort_children(self) -> None:
        # Sort the list by name
        self.children.sort(key=lambda item: item.name)
        # Sort the list so that folders are first
        self.children.sort(key=lambda item: item.isfile)

    def rename(self, new_name:str) -> None:
        #if self.master is None:
        #    self.full_path = self.full_path.rstrip(self.name) + new_name
        #else:
        self.full_path = self.master.full_path + "/" + new_name
        self.name = new_name
        if self.isfile:
            self.set_extension()


class Folder(Item):
    def __init__(self, name:str=None, master=None, expanded:bool=False):
        self.expanded = expanded
        self.children = []
        self.isfile = False
        # `name` is `None` only when this class is being inherited by BaseExplorer
        if name == None:
            self.master = None
            self.name = ""
            self.expanded = True
        else:
            # Calculate the 
            if master is None:
                self.full_path = name
                name = name.split("/")[-1]
            else:
                self.full_path = master.full_path + "/" + name

            super().__init__(name, master)
            self._update()

    def __iter__(self):
        return iter(self.children)

    def _update(self) -> None:
        """
        Updates `self.children` with a new list with the new files/folders.
        """
        # Get the current children names:
        current_children_names = tuple(item.name for item in self.children)
        old_children = self.children.copy()
        self.children.clear()
        # Get a list of the files+folders in the folder
        try:
            names = os.listdir(self.full_path)
        except PermissionError:
            names = []
        # If there are too many files, add a file called "..."
        if len(names) > MAX_FILES_PER_FOLDER:
            names = names[:SHOW_MAX_FILES_PER_FOLDER]
            names.append("...")
        # Hide all of the "__pycache__" folders:
        names = tuple(filter(lambda item: item != "__pycache__", names))
        for name in names:
            # If the file/folder was in `self.children` re-add it
            if name in current_children_names:
                idx = current_children_names.index(name)
                item = old_children[idx]
                item._update()
            else:
                full_path = self.full_path + "/" + name
                if os.path.isdir(full_path) and (name != "..."):
                    item = Folder(name, master=self)
                else:
                    item = File(name, master=self)
            self.children.append(item)
        self.sort_children()
        for child in old_children:
            if child not in self.children:
                child.garbage_collect = True

    def to_string(self) -> str:
        # If we shouldn't expanded `return None`
        if not self.expanded:
            return ""
        output = ""
        for item in self.children:
            # Get that item's indentation
            indentation = item.indentation
            # If it's a file show it
            if item.isfile:
                output += " "*(4*indentation) + item.name + "\n"
            # If it's a folder show it then show it's contents
            else:
                # Show the folder
                if item.expanded:
                    symbol = "-"
                else:
                    symbol = "+"
                output += " "*(4*indentation) + symbol + " " + item.name + "\n"
                # Show the folder's contents
                output += item.to_string()
                # If the folder is empty make sure that there isn't a "\n\n":
                output = output.strip("\n") + "\n"
        return output[:-1]

    def add_item(self, item) -> None:
        if not isinstance(item, Item):
            raise ValueError(f"`item` must be a `File/Folder` not {type(item)}")
        self.children.append(item)
        item.master = self
        item.fix_indentation()

    def add_folder(self, folder:str) -> None:
        if not isinstance(item, str):
            raise ValueError(f"`folder` must be a `str` not {type(item)}")
        self.add_item(Folder(folder))

    def add_file(self, file:str) -> None:
        if not isinstance(item, str):
            raise ValueError(f"`file` must be a `str` not {type(item)}")
        self.add_item(File(file))


class File(Item):
    def __init__(self, name:str, master:Folder):
        super().__init__(name, master)
        self.isfile = True
        self.set_extension()

    def set_extension(self) -> None:
        extension = self.name.split(".")[-1]
        if extension in KNOWN_EXT:
            self.extension = extension
        else:
            self.extension = "file"


class BaseExplorer(Folder):
    def __init__(self):
        super().__init__()

    def add(self, folder:str) -> None:
        """
        Adds a folder to the list of fodlers to be displayed. Please
        note that the input must be a folder.
        """
        full_path = os.path.abspath(folder).replace("\\", "/")
        folder = Folder(full_path)
        self.children.append(folder)

    def remove(self, folder:str) -> None:
        """
        Removes a folder that was added using the `.add` method.
        Raises `ValueError`, if the folder isn't in `self.children`
        """
        full_path = os.path.abspath(folder).replace("\\", "/")
        for child in self.children:
            if child.full_path == full_path:
                self.children.remove(child)
                return None
        raise ValueError("Can't remove that folder because it wasn't added.")

    def _update(self) -> None:
        """
        Update the tree.
        """
        for child in self.children:
            child._update()


if __name__ == "__main__":
    from sys import stderr
    stderr.write("="*80)

    explorer = BaseExplorer()
    explorer.add(".")
    print(explorer.to_string())

    print("="*80)
    test = explorer.children[0].children[1]
    images = explorer.children[0].children[0]

    print(test, "=>", images)
    print("="*80)
    test.move_to(images)
    print(explorer.to_string())


    stderr.write("="*80)


    explorer = BaseExplorer()
    explorer.add(".")
    print(explorer.to_string())

    print("="*80)
    test = explorer.children[0].children[1]
    images = explorer.children[0].children[0]

    print(images, "=>", test)
    print("="*80)
    images.move_to(test)
    print(explorer.to_string())


    print("="*80)
    try2 = explorer.children[0]
    print(images, "=>", try2)
    print("="*80)
    images.move_to(try2)
    print(explorer.to_string())


"""
explorer.temp_holder = tk.Frame()
explorer.selected = explorer.shown_items[5]
explorer.dragging_file = True
explorer.offset_y = 0
explorer.event_generate("<Motion>", warp=True, x=146, y=162)
"""

"""
explorer.last_taken_row
[i.item for i in explorer.shown_items]
[(i, j) for i, j in explorer.item_to_idx.items()]
"""


"""
slow_item_to_idx
slow_item_to_frame
fix_item_to_idx
item_to_idx

self.shown_items
"""
