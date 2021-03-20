from PIL import Image, ImageTk
from itertools import chain
import tkinter as tk
import shutil
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

ILLEGAL_FILE_NAMES = ("$Mft", "$MftMirr", "$LogFile", "$Volume", "$AttrDef",
                      "$Bitmap", "$Boot", "$BadClus", "$Secure", "$Upcase",
                      "$Extend", "$Quota", "$ObjId", "$Reparse", "CON", "PRN",
                      "AUX", "CLOCK$", "NUL", "COM0", "COM1", "COM2", "COM3",
                      "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT0",
                      "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7",
                      "LPT8", "LPT9", "LST", "KEYBD$", "SCREEN$", "$IDLE$",
                      "CONFIG$")
ILLEGAL_FILE_CHARS = "\\/:*?\"<>|%" # \/:*?"<>|%


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
        group = self.get_group(item)
        for group_item in group:
            super().move(group_item, dx, dy)

    def tag_raise(self, tag):
        group = self.get_group(tag)
        for group_item in group:
            super().tag_raise(group_item)

    def get_group(self, item):
        for group in self.groups:
            if item in group:
                return group
        raise ValueError("The item isn't in a group.")


class FileExplorer(tk.Frame):
    def __init__(self, master, font=None, width=150, height=200, bg="black",
                 fg="white", pady=5, padx1=10, padx2=5, refresh_time=3000,
                 select_colour="#0000a0", **kwargs):
        """
        Note:
            `padx1` is between the left edge and the first `+`/`-`
            `padx2` is between the `+`/`-` and the text
            `pady` is between the top edge and the start of the text
        """
        super().__init__(master, bd=0, highlightthickness=0)
        self.canvas = GroupedCanvas(self, height=height, width=width, bg=bg,
                                    **kwargs)
        self.scrollbar = tk.Scrollbar(self, command=self.canvas.yview)
        self.canvas.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(fill="y", side="right")
        self.canvas.pack(fill="both", expand=True, side="left")
        self.bg = bg
        self.fg = fg
        self.font = font
        self.pady = pady
        self.padx1 = padx1
        self.padx2 = padx2
        self.width = width
        self.height = height
        self.refresh_time = refresh_time
        self.select_colour = select_colour

        self.text_height = self.get_text_height()
        self.box_height = self.text_height * 1.2
        self.arrow_width = self.get_arrow_width() + 2

        self.file_structure = []
        self.caller_added_folders = []
        self.reset()

        self.idx = 0
        self.tkimgs = [] # A list so that gc doesn't collect out images

        self.rectangle_selected = None
        self.selected_file_idx = None
        self.selected_file = None

        self.button1_down = False
        self.renaming = False
        self.dragging = False
        self.refreshing = True

        self.menu = tk.Menu(self, tearoff=False, bg=bg, fg=fg, bd=0)
        self.menu.add_command(label="Rename", command=self.rename)
        self.menu.add_command(label="Delete", command=self.delete)

        self.canvas.bind("<Button-1>", self.mouse_down)
        self.canvas.bind("<Button-3>", self.open_menu)
        self.canvas.bind("<B1-Motion>", self.mouse_motion)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)
        self.canvas.bind("<Double-Button-1>", self.open_file)

        self.bind("<<_FolderSelected>>", self.on_select)
        self.bind("<<_FileSelected>>", self.on_select)

        self.bind_all("<Control-r>", self.refresh)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        self.refresh_loop()

    def open_menu(self, event):
        if self.renaming:
            return None
        self.select(event, False)
        self.menu.tk_popup(event.x_root, event.y_root)
        self.menu.grab_release()

    def delete(self):
        if self.selected_file is None:
            return None
        try:
            *_, full_path = self.shown_files_dict[self.selected_file]
            os.remove(full_path)
        except:
            pass

    def rename(self):
        if self.selected_file is None:
            return None
        self.refreshing = False
        self.renaming = True
        file = self.selected_file
        idx, canvas_ids, isdir, full_path = self.shown_files_dict[file]
        r, t, img = canvas_ids
        self.canvas.tag_raise(r)

        x, y, *_ = self.canvas.bbox(t)

        self.renaming_entry = tk.Entry(self.canvas, bg=self.bg, fg=self.fg,
                                       insertbackground=self.fg, font=self.font)
        self.renaming_entry_id = self.canvas.create_window(x, y,
                                     window=self.renaming_entry, anchor="nw")
        self.renaming_entry.focus()

        self.renaming_entry.insert("end", file.split("/")[-1])
        self.renaming_entry.select_range(0, "end")
        self.renaming_entry.icursor("end")

        self.renaming_entry.bind("<Escape>", self.rename_escape)
        self.renaming_entry.bind("<Return>", self.rename_done)

        self.renaming_entry.filename = file
        self.renaming_entry.full_path = full_path
        self.renaming_entry.idx = idx

    def rename_escape(self, event=None):
        self.refresh()
        self.refreshing = True
        self.renaming = False

    def illegal_file_name_rename(self):
        # Tell the user thatthey entered a wrong filename
        root = tk.Toplevel(self)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        x, y, *_ = self.canvas.bbox(self.renaming_entry_id)
        x += self.canvas.winfo_rootx()
        y += self.canvas.winfo_rooty()
        root.geometry("+%i+%i" % (x, y))
        tk.Label(root, text="Illegal char/filename.", bg="orange").pack()
        root.after(1500, root.destroy)

        self.refresh()
        self.refreshing = True
        self.renaming = False

    def rename_done(self, event):
        new_file_name = self.renaming_entry
        new_file = new_file_name.get()

        # Check if the name is legal:
        if len(new_file) == 0:
            self.illegal_file_name_rename()
            return None
        if new_file in ILLEGAL_FILE_NAMES:
            self.illegal_file_name_rename()
            return None
        for char in ILLEGAL_FILE_CHARS:
            if char in new_file:
                self.illegal_file_name_rename()
                return None

        idx = self.renaming_entry.idx
        old_full_path = self.renaming_entry.full_path

        new_full_path = "\\".join(old_full_path.split("\\")[:-1] + [new_file])
        try:
            os.rename(old_full_path, new_full_path)
        except:
            pass

        self.refresh()
        self.refreshing = True
        self.renaming = False

    def refresh_loop(self):
        if (not self.dragging) and self.refreshing:
            self.refresh()
        self.after(self.refresh_time, self.refresh_loop)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta/120), "units")

    def mouse_down(self, event):
        if self.renaming:
            self.rename_escape()
        self.select(event)
        self.mouse_lastx = self.canvas.canvasx(event.x)
        self.mouse_lasty = self.canvas.canvasy(event.y)

    def on_select(self, event):
        self.button1_down = True
        self.dragging = False

    def mouse_up(self, event):
        self.button1_down = False
        if self.dragging:
            self.dragging = False
            moving_file_idx = self.selected_file_idx
            this_file = self.idx_to_full_path[moving_file_idx]
            new_idx = self.pos_to_idx(self.canvas.canvasy(event.y))
            if new_idx >= self.idx:
                new_idx = 0
            if new_idx < 0:
                self.redraw_tree()
                return None
            new_file = self.idx_to_file[new_idx]

            new_file_location_data = self.shown_files_dict[new_file]
            new_dir = new_file_location_data[3]
            if not new_file_location_data[2]:
                new_dir = os.path.dirname(new_dir)

            try:
                shutil.move(this_file, new_dir)
                self.refresh()
            except:
                self.redraw_tree()

    def refresh(self, event=None):
        selected_file = self.selected_file
        old_file_structure = self.file_structure
        caller_added_folders = self.caller_added_folders
        self.caller_added_folders = []
        self.file_structure = []
        for args in caller_added_folders:
            self.add_dir(*args)
        self.scared_copy_file_structure(old_file_structure)
        self.redraw_tree()
        try:
            self._select(selected_file)
        except:
            pass

    def mouse_motion(self, event):
        try:
            if not self.button1_down:
                return None
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            moving = self.pos_to_idx(y) == self.selected_file_idx
            if moving and (not self.dragging):
                return None
            self.dragging = True
            if self.button1_down:
                dx, dy = x - self.mouse_lastx, y - self.mouse_lasty
                self.canvas.move(self.rectangle_selected, dx, dy)
                self.canvas.tag_raise(self.rectangle_selected)
            self.mouse_lastx = x
            self.mouse_lasty = y
        except:
            pass

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
        self.caller_added_folders.append((parent, folder, expanded))
        self.redraw_tree()

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

    def scared_copy_file_structure(self, scared_file_structure,
                                   actual_tree=None):
        """
        Coppies only the `expanded` part of `scared_file_structure`
        into `self.file_structure``
        """
        if actual_tree is None:
            actual_tree = self.file_structure
        for item in actual_tree:
            if len(item) != 2:
                found = None
                for candidate_item in scared_file_structure:
                    if found is not None:
                        continue
                    if len(candidate_item) != 2:
                        if candidate_item[-1] == item[-1]:
                            found = candidate_item
                if found is not None:
                    item[2] = found[2]
                    self.scared_copy_file_structure(found[1],
                                                    item[1])

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
        maxy = max(self.canvas.winfo_height() - 4,
                   self.idx_to_pos(self.idx) + self.pady)
        self.canvas.config(scrollregion=(0, 0, self.width, maxy))

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

    def select(self, event, open_dir=True):
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
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        idx = self.pos_to_idx(y)
        if idx >= self.idx:
            self.unselect()
            return None

        file = self.idx_to_file[idx]
        _, canvas_ids, isdir, full_path = self.shown_files_dict[file]

        if isdir:
            if open_dir:
                # Check if `+` or `-` is pressed:
                bbox = self.canvas.bbox(canvas_ids[2])
                if bbox[0] <= x <= bbox[2]:
                    self._open_folder(idx, file)
                    return None
            self.event_generate("<<FolderSelected>>", when="tail")
            self.event_generate("<<_FolderSelected>>", when="tail")
        else:
            self.event_generate("<<FileSelected>>", when="tail")
            self.event_generate("<<_FileSelected>>", when="tail")
        self._select(file)

    def unselect(self):
        # Change the selected rectangle's bg to `self.select_colour`
        if self.rectangle_selected is not None:
            self.canvas.itemconfig(self.rectangle_selected, fill=self.bg)
            self.rectangle_selected = None
            self.selected_file = None
            self.selected_file_idx = None

    def _select(self, file):
        if file is None:
            return None
        idx, canvas_ids, isdir, full_path = self.shown_files_dict[file]
        rectangle = canvas_ids[0]
        self.unselect()
        self.rectangle_selected = rectangle
        self.selected_file = file
        self.selected_file_idx = idx
        self.canvas.itemconfig(rectangle, fill=self.select_colour)

    def open_file(self, event):
        y = self.canvas.canvasy(event.y)
        idx = self.pos_to_idx(y)
        if idx >= self.idx:
            return None

        file = self.idx_to_file[idx]
        _, canvas_ids, isdir, full_path = self.shown_files_dict[file]

        if isdir:
            self._open_folder(idx, file)
        else:
            self.event_generate("<<FileOpened>>", when="tail")

    def search_filestructure(self, file, tree=None):
        if tree is None:
            tree = self.file_structure
        for item in tree:
            if item[0] == file:
                return item
            if len(item) != 2:
                result = self.search_filestructure(file, item[1])
                if result is not None:
                    return result

    def search_filestructure_full_path(self, file, tree=None):
        if tree is None:
            tree = self.file_structure
        for item in tree:
            if item[-1] == file:
                return item
            if len(item) != 2:
                result = self.search_filestructure(file, item[1])
                if result is not None:
                    return result

    def _open_folder(self, idx, file):
        full_path = self.idx_to_full_path[idx]
        self.event_generate("<<FolderOpened>>", when="tail")

        searching_for = self.search_filestructure(file)
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
        if self.selected_file is None:
            return None
        try:
            _, (rectangle, *_), *_ = self.shown_files_dict[self.selected_file]
            self.rectangle_selected = rectangle
            self.canvas.itemconfig(rectangle, fill=self.select_colour)
        except KeyError:
            pass

    def idx_to_pos(self, idx):
        """
        Converts `idx` to y position. The `pady` is there because otherwise
        the whole tree is too high (no pady)
        """
        return idx * self.box_height + self.pady

    def pos_to_idx(self, pos):
        """
        Converts `idx` to y position. The `pady` is there because otherwise
        the whole tree is too high (no pady)
        """
        return int((pos - self.pady) / self.box_height)


if __name__ == "__main__":
    def opened(event):
        pass
        # print("Opened a folder")

    def selected(event):
        pass
        # print("Selected:", explorer.selected_file)


    root = tk.Tk()
    explorer = FileExplorer(root, width=200, height=300, font=("", 13))
    explorer.pack(expand=True, fill="both")

    explorer.add_dir(".", "test folder")

    explorer.bind("<<FileOpened>>", opened)
    explorer.bind("<<FolderOpened>>", opened)

    explorer.bind("<<FileSelected>>", selected)
    explorer.bind("<<FolderSelected>>", selected)

    root.mainloop()
