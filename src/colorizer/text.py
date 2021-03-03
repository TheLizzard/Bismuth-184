from basiceditor.text import LinedScrolledBarredText
from colorizer.colorizer import ColorDelegator
from idlelib.percolator import Percolator


class ColouredLinedScrolledBarredText(LinedScrolledBarredText):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        percolator = Percolator(self)
        delegator = ColorDelegator()
        percolator.insertfilter(delegator)
        super().init()
