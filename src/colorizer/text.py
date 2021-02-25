from basiceditor.text import ScrolledBarredText
from colorizer.colorizer import Percolator, ColorDelegator


class ColouredScrolledBarredText(ScrolledBarredText):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        percolator = Percolator(self)
        delegator = ColorDelegator()
        percolator.insertfilter(delegator)
        super().init()
