class Tag:
    __slots__ = ("text", "value")

    def __init__(self, text, value):
        self.value = value
        self.text = text

    def __repr__(self):
        return f"Tag({self.value})"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return self.value == other.value

    def __ge__(self, other):
        # self >= other
        if self.value == "-":
            return False
        if other.value == "+":
            return False
        if self.value == "+":
            return True
        if other.value == "-":
            return True
        return self.text.compare(self.value, ">=", other.value)

    def __gt__(self, other):
        # self > other
        if self.value == "-":
            return False
        if other.value == "+":
            return False
        if self.value == "+":
            return True
        if other.value == "-":
            return True
        return self.text.compare(self.value, ">", other.value)

    def __le__(self, other):
        # self <= other
        if self.value == "-":
            return True
        if other.value == "+":
            return True
        if self.value == "+":
            return False
        if other.value == "-":
            return False
        return self.text.compare(self.value, "<=", other.value)

    def __lt__(self, other):
        # self < other
        if self.value == "-":
            return True
        if other.value == "+":
            return True
        if self.value == "+":
            return False
        if other.value == "-":
            return False
        return self.text.compare(self.value, "<", other.value)


class Range:
    __slots__ = ("text", "data")

    def __init__(self, text):
        self.text = text
        self.data = [[Tag(text, "-"), Tag(text, "-")],
                     [Tag(text, "1.0"), Tag(text, text.index("end-1c"))],
                     [Tag(text, "+"), Tag(text, "+")]]

    def subtract_range(self, start, end):
        # Sometimes we get a `_tkinter.Tcl_Obj` object instead of a str for
        # start/end. Raises `TypeError: __str__ returned
        # non-string (type _tkinter.Tcl_Obj)`
        start = Tag(self.text, str(start))
        end = Tag(self.text, str(end))
        handled = False
        for i, (idx1, idx2) in enumerate(self.data):
            if (idx1 <= start) and (idx2 >= end):
                # Test 1
                self.data[i] = [idx1, start]
                self.data.insert(i+1, [end, idx2])
                handled = True
            elif (idx2 <= start) and (end <= self.data[i+1][0]):
                # Test 4
                handled = True
            elif (idx1 >= start >= self.data[i-1][1]) and (idx2 >= end):
                # Test 2
                self.data[i][0] = end
                handled = True
            elif (idx2 <= end <= self.data[i+1][0]) and (idx1 <= start):
                # Test 5
                self.data[i][1] = start
                handled = True
            elif (idx1 <= start <= idx2) and (self.data[i+1][0] <= end <= self.data[i+1][1]):
                self.data[i][1] = start
                self.data[i+1][0] = end
                handled = True

            if handled:
                self.clean_up()
                break

        if not handled:
            print(self.data)
            raise ValueError("Couldn't subract range:", (start, end))

    def clean_up(self):
        for i, (idx1, idx2) in enumerate(self.data[1:-1]):
            if idx1 > idx2:
                print(self.data)
                print((idx1, idx2))
                raise ValueError("For some reason the range is upside down.")
            if idx2 == idx1:
                del self.data[i]

    def tolist(self):
        return tuple((str(start), str(end)) for start, end in self.data[1:-1])


if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    text = tk.Text(root)
    text.insert("end", "Microsoft Windows [Version 10.0.19041.804]\r\n(c) 2020 Microsoft Corporation. All rights reserved.\r\n\r\nC:\\Users\\TheLizzard\\Documents\\GitHub\\CPP-IDLE\\src>cmd\n \n")
    text.tag_config("readonly", background="light grey")
    text.tag_add("readonly", "1.0", "4.50")
    text.pack()
    _range = Range(text)
    _range.subtract_range("1.0", "4.50")
    print(_range.data)
