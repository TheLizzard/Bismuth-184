try:
    from .bettertk import *
    from .betterframe import BetterFrame
    from .betterscrollbar import BetterScrollBarVertical, \
                                 BetterScrollBarHorizontal, \
                                 ScrolledText
except ImportError:
    from bettertk import *
    from betterframe import BetterFrame
    from betterscrollbar import BetterScrollBarVertical, \
                                BetterScrollBarHorizontal, \
                                ScrolledText


if __name__ == "__main__":
    root = BetterTk()

    text = ScrolledText(root, width=80, height=20, wrap="none", hscroll=True)
    line = " ".join(map(str, range(50)))
    text.insert("end", "\n".join(line for i in range(25)))
    text.pack(fill="both", expand=True)

    root.mainloop()
