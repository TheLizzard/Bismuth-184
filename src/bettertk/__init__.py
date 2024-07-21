try:
    from .bettertk import *
    from .betterframe import BetterFrame
    from .betterentry import BetterEntry
    from .betterscrollbar import BetterScrollBarVertical, \
                                 BetterScrollBarHorizontal, \
                                 make_scrolled
except ImportError:
    from bettertk import *
    from betterframe import BetterFrame
    from betterentry import BetterEntry
    from betterscrollbar import BetterScrollBarVertical, \
                                BetterScrollBarHorizontal, \
                                make_scrolled

BetterScrollBarV:type = BetterScrollBarVertical
BetterScrollBarH:type = BetterScrollBarHorizontal


if __name__ == "__main__":
    root = BetterTk(className="BetterTk")
    root.title("BetterTk")

    text:tk.Text = tk.Text(root, bg="black", fg="white", width=80, height=20,
                           bd=0, highlightthickness=0, insertbackground="white",
                           wrap="none")

    text.insert("end", "\n".join(" ".join(map(str, range(i+1))) for i in range(100)))

    make_scrolled(root, text, vscroll=True, hscroll=True, lines_numbers=True)

    root.mainloop()


if __name__ == "__main__":
    root = BetterTk(className="BetterTk")
    root.title("BetterTk")

    frame = BetterFrame(root, height=200, hscroll=False, vscroll=True,
                        VScrollBarClass=BetterScrollBarVertical, bg="black")
    frame.pack()

    for i in range(30):
        tk.Label(frame, text=f"{i}", bg="red", fg="white").pack(fill="x")

    root.mainloop()