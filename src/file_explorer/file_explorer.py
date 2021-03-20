from PIL import Image, ImageTk
from itertools import chain
import tkinter as tk
import os


ARROW_CLOSED = "+"
ARROW_OPENED = "-"

HEADER_FILE_IMG = Image.open("images/header file.png")
CPP_FILE_IMG = Image.open("images/c++ file.png")
OTHER_FILE_IMG = Image.open("images/other file.png")

EXTENTION_TO_IMG = {".h": HEADER_FILE_IMG,
                    ".cpp": CPP_FILE_IMG,
                    ".c++": CPP_FILE_IMG,
                    "other": OTHER_FILE_IMG}


class GroupedCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.groups = []

    def group(self, *items):
        for item in items:
            if item in chain.from_iterable(self.groups):
                raise ValueError("This item has already been grouped.")
        self.groups.append(items)

    def move(self, item, dx, dy):
        if item in chain.from_iterable(self.groups):
            for group in self.groups:
                if item in group:
                    for group_item in group:
                        super().move(group_item, dx, dy)
                    return None
            raise Exception("An error occured. GL figuring it out")
        super().move(item, dx, dy)


class FileExplorer(tk.Frame):
    def __init__(self, master, font=None, width=150, bg="black", fg="white",
                 pady=5, padx1=10, padx2=5, **kwargs):
        """
        Note:
            `padx1` is between the left edge and the first `+`/`-`
            `padx2` is between the `+`/`-` and the text
            `pady` is between the top edge and the start of the text
        """
        super().__init__(master, bd=0, highlightthickness=0)
        self.canvas = GroupedCanvas(self, width=width, bg=bg, **kwargs)
        self.canvas.pack(fill="both", expand=True)

        self.bg = bg
        self.fg = fg
        self.font = font
        self.pady = pady
        self.padx1 = padx1
        self.padx2 = padx2
        self.width = width

        self.text_height = self.get_text_height()
        self.box_height = self.text_height * 1.2
        self.arrow_width = self.get_arrow_width() + 2

        self.file_structure = []
        self.reset()

        self.idx = 0
        self.tkimgs = [] # A list so that gc doesn't collect out images
        self.rectangle_selected = None
        self.file_selected = None

        self.canvas.bind("<Button-1>", self.select)
        self.canvas.bind("<Double-Button-1>", self.open_file)

    def reset(self):
        self.canvas.delete("all")
        self.idx = 0
        self.shown_files_dict = {} # file: (idx, (canvas_ids), isdir, full_path)
        self.idx_to_file = {} #      idx: file
        self.idx_to_full_path = {}#  idx: full_path

    def get_text_height(self):
        """
        Used to get the height of the text that will be displayed
        """
        bbox = self.get_bbox("abcdefghijklmnopqrstuvwxyz")
        return bbox[3] - bbox[1]

    def get_arrow_width(self):
        """
        Used to get the width of the `+` or `-` that will be displayed
        """
        bbox = self.get_bbox("+-")
        return (bbox[2] - bbox[0])/2

    def get_bbox(self, text):
        """
        Used to get the bbox of a sequence of text to test
        the size of the font
        """
        test = self.canvas.create_text(0, 0, text=text, font=self.font)
        bbox = self.canvas.bbox(test)
        self.canvas.delete(test)
        return bbox

    def add_dir(self, parent, folder, expanded=True):
        """
        Adds a dir to the folders list.
        Call `<FileExplorer>.redraw_tree()` to update the display
        """
        file_structure = self._add_dir(parent, folder)
        self.file_structure.append([folder, file_structure, expanded,
                                    os.path.abspath(parent + "/" + folder)])

    def _add_dir(self, root_path, folder_searching):
        """
        Converts all of the files in the folders to a list recursively.
        In the form of [(folder, [*files], expanded), file1, file2]
        """
        output = []
        full_path = os.path.abspath(root_path + "/" + folder_searching)
        for file in self.get_all_files_folders(full_path):
            file_path = os.path.abspath(full_path + "/" + file)
            if os.path.isdir(file_path):
                new_folder_searching = folder_searching + "/" + file
                file_structure = self._add_dir(root_path, new_folder_searching)
                output.append([new_folder_searching, file_structure, False,
                               file_path])
            else:
                output.append((folder_searching + "/" + file, file_path))
            continue
        return output

    def get_all_files_folders(self, path):
        """
        Gets all of the files and folders out of a folder by using `os.walk`
        on dir up (instead of `os.walk("foo/bar")` it does `os.walk("bar")`)
        That gives all of the folders and files in the path.

        Note: If sorting is going to be implemented, it should be here

        returns in the form [folder1, folder2, file1, file2, file3]
            can be a tuple/iterator
        """
        output = []
        data = os.walk("\\".join(path.split("\\")[:-1]))
        for candidate_path, dirs, files in data:
            if candidate_path == path:
                return dirs + files

    def redraw_tree(self):
        """
        Redraws all of the sprites.
        """
        self.reset()
        self._redraw_tree(self.file_structure)

    def _redraw_tree(self, tree):
        """
        Redraws all of the sprites recursively
        """
        for item in tree:
            if len(item) == 2:
                # Normal file
                self.display_file(item)
            else:
                # A folder
                self.display_file(item)
                if item[2]:
                    self._redraw_tree(item[1])

    # Displays a file
    def display_file(self, file):
        """
        Displays a file like this:
         - folder1
           █ file1
           █ file2
         █ file3
        where `█` is the icon of that type of file.
        """
        # `r` is the rectangle
        # `t` is the text
        # `img` is the file image/arrow
        if len(file) == 2:
            # A normal file
            isfolder = False
            filename, full_path = file
            # Get the correct image sprite:
            extention = "." + filename.split(".")[-1]
            if extention in EXTENTION_TO_IMG:
                pil_img = EXTENTION_TO_IMG[extention]
            else:
                pil_img = EXTENTION_TO_IMG["other"]
        else:
            # A folder
            filename, _, shown, full_path = file
            isfolder = True
            if shown:
                arrow = ARROW_OPENED
            else:
                arrow = ARROW_CLOSED

        indentation = filename.count("/") * self.arrow_width

        starty = self.idx_to_pos(self.idx)
        endy = self.idx_to_pos(self.idx + 1)
        r = self.canvas.create_rectangle(0, starty, self.width, endy,
                                         fill=self.bg)
        y = starty + self.box_height * 0.1
        x = self.padx1 + self.padx2 + indentation + self.arrow_width
        text = filename.split("/")[-1]
        t = self.canvas.create_text(x, y, text=text, fill=self.fg,
                                    font=self.font, anchor="nw")

        x -= self.arrow_width + self.padx2
        if isfolder:
            img = self.canvas.create_text(x, y, text=arrow, fill=self.fg,
                                          font=self.font, anchor="nw")
        else:
            width = int(self.arrow_width + 0.5)
            height = int(self.text_height + 0.5)
            pil_image = pil_img.resize((width, height), Image.NEAREST)
            tkimg = ImageTk.PhotoImage(pil_image)
            img = self.canvas.create_image(x, y, image=tkimg, anchor="nw")
            self.tkimgs.append(tkimg)

        self.shown_files_dict.update({filename: [self.idx, (r, t, img),
                                                 isfolder, full_path]})
        self.idx_to_file.update({self.idx: filename})
        self.idx_to_full_path.update({self.idx: full_path})
        self.canvas.group(r, t, img)
        self.idx += 1

    def select(self, event):
        """
        When ever the user clicks on a folder/file.
        Check if it is a folder or a file
        if file:
            select that file
        else:
            if user clicked on the `+` or `-`:
                hide the folder contents
            else:
                select the folder
        """
        x = self.canvas.canvasy(event.x)
        y = self.canvas.canvasy(event.y)
        idx = int((y - self.pady) / self.box_height)
        if idx >= self.idx:
            return None

        file = self.idx_to_file[idx]
        _, canvas_ids, isdir, full_path = self.shown_files_dict[file]
        rectangle = canvas_ids[0]

        if isdir:
            # Check if `+` or `-` is pressed:
            bbox = self.canvas.bbox(canvas_ids[2])
            if bbox[0] <= x <= bbox[2]:
                self._open_folder(idx, file)
                return None
            self.event_generate("<<FolderSelected>>", when="tail")
        else:
            self.event_generate("<<FileSelected>>", when="tail")

        # Change the selected rectangle's bg to "#0000a0"
        if self.rectangle_selected is not None:
            self.canvas.itemconfig(self.rectangle_selected, fill=self.bg)
        self.rectangle_selected = rectangle
        self.file_selected = file
        self.canvas.itemconfig(rectangle, fill="#0000a0")

    def open_file(self, event):
        y = self.canvas.canvasy(event.y)
        idx = int((y - self.pady) / self.box_height)
        if idx >= self.idx:
            return None

        file = self.idx_to_file[idx]
        _, canvas_ids, isdir, full_path = self.shown_files_dict[file]

        if isdir:
            self._open_folder(idx, file)
        else:
            self.event_generate("<<FileOpened>>", when="tail")

    def _open_folder(self, idx, file):
        full_path = self.idx_to_full_path[idx]
        self.event_generate("<<FolderOpened>>", when="tail")

        # Find the folder's list location in self.file_structure
        # So the we can change its `shown` value
        trees = [self.file_structure]
        searching_for = None
        while searching_for is None:
            if len(trees) == 0:
                raise ValueError("An error occured. GL solving it.")
            tree = trees.pop()
            for item in tree:
                if not isinstance(item, str):
                    if item[0] == file:
                        searching_for = item
                        break
                    trees.append(item[1])
        _, files_inside_folder, already_shown, fill_path = searching_for
        # Change the `show` value
        searching_for[2] = not already_shown
        # Change the arrow from `ARROW_CLOSED` to `ARROW_OPENED`
        # and vice versa
        _, (_, _, img), _, _ = self.shown_files_dict[file]
        if already_shown:
            self.canvas.itemconfig(img, text=ARROW_CLOSED)
        else:
            self.canvas.itemconfig(img, text=ARROW_OPENED)
        # Redraw the whole screen
        self.redraw_tree()
        # Select the previously selected file
        if self.file_selected is None:
            return None
        try:
            _, (rectangle, *_), *_ = self.shown_files_dict[self.file_selected]
            self.rectangle_selected = rectangle
            self.canvas.itemconfig(rectangle, fill="#0000a0")
        except KeyError:
            pass

    def idx_to_pos(self, idx):
        """
        Converts `idx` to y position. The `+5` is there because otherwise
        the whole tree is too high (no pady)
        """
        return idx * self.box_height + self.pady


if __name__ == "__main__":
    def opened(event):
        print("Opened a folder")

    def selected(event):
        print("Selected:", explorer.file_selected)


    root = tk.Tk()
    explorer = FileExplorer(root, width=200, height=300, font=("", 13))
    explorer.pack(expand=True, fill="both")

    explorer.add_dir(".", "test folder")
    explorer.redraw_tree()

    explorer.bind("<<FileOpened>>", opened)
    explorer.bind("<<FolderOpened>>", opened)

    explorer.bind("<<FileSelected>>", selected)
    explorer.bind("<<FolderSelected>>", selected)

    # root.mainloop()
