from basiceditor.text import BarredScrolledLinedText
from colorizer.colorizer import ColorDelegator
from idlelib.percolator import Percolator


class ColouredLinedScrolledBarredText(BarredScrolledLinedText):
    def __init__(self, master, **kwargs):
        super().__init__(master, call_init=False, **kwargs)
        percolator = Percolator(self)
        delegator = ColorDelegator()
        percolator.insertfilter(delegator)
        super().init()
