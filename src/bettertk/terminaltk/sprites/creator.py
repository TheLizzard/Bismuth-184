from __future__ import annotations
from math import pi, sqrt, sin as _sin, cos as _cos, tan as _tan, atan as _atan
from PIL import Image, ImageTk
from time import perf_counter
from typing import Callable
import tkinter as tk


ALL_SPRITE_NAMES:set[str] = {
    "pause-green", "pause-black",
    "play-green", "play-black",
    "exclam-red", "exclam-orange", "exclam-blue",
    "x-red", "x-orange",
    "i-red", "i-orange", "i-blue", "i-black",
    "tick-green", "tick-black",
    "restart", "restart-blue", "restart-black",
    "warning",
    "io-red",
    "plus-black", "plus-grey",
    "gear-white", "gear-grey",
    "spinner1", "spinner2", "spinner3", "spinner4",
    "spinner5", "spinner6",
    "spinner6-black",
}

SPRITES_REMAPPING:dict[str:str] = {"stop":"exclam-orange",
                                   "info":"exclam-blue",
                                   "kill":"io-red",
                                   "error":"x-red",
                                   "close":"x-orange",
                                   "settings":"gear-white"}
RSPRITES_REMAPPING:dict[str:str] = {v:k for k,v in SPRITES_REMAPPING.items()}

Colour:type = tuple[int,int,int]

ε:float = 0.01
BLACK:Colour = (0,0,0)
WHITE:Colour = (255,255,255)
RED:Colour = (255,0,0)
GREEN:Colour = (0,255,0)
BLUE:Colour = (0,0,255)
CYAN:Colour = (0,255,255)
DGREEN:Colour = (0,180,0)
YELLOW:Colour = (255,255,0)
ORANGE:Colour = (255,165,0)
DYELLOW:Colour = (252,225,0)
DGREY:Colour = (70,70,70)
sin:Function[float,float] = lambda deg: _sin(deg/180*pi)
cos:Function[float,float] = lambda deg: _cos(deg/180*pi)
tan:Function[float,float] = lambda deg: _tan(deg/180*pi)
atan:Function[float,float] = lambda x: _atan(x)/pi*180
sq:Function[float,float] = lambda x: x*x
sign:Function[float,float] = lambda x: (2*(x>0)-1)*(x!=0)
line_gradient:Function = lambda x1,y1,x2,y2: div(y2-y1, x2-x1)
div:Function[float,float,float] = lambda a,b: (a/ε if b == 0 else a/b)
def fatan(x:float, y:float) -> float:
    assert not (x == y == 0), "Fatan of (0,0) doesn't exist"
    if x == 0:
        return 270-180*(y>0)
    if x < 0:
        return atan(y/x)+180
    return atan(y/x)%360
map_int = lambda *a:map(int, a)


# Taken from: https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm
def _get_line_low(result, x0, y0, x1, y1) -> None:
    dx = x1 - x0
    dy = y1 - y0
    yi = 1
    if dy < 0:
        yi = -1
        dy = -dy
    D = (2 * dy) - dx
    y = y0
    for x in range(x0, x1+1):
        result[y] = x
        if D > 0:
            y = y + yi
            D = D + (2 * (dy - dx))
        else:
            D = D + 2*dy

def _get_line_high(result, x0, y0, x1, y1) -> None:
    dx = x1 - x0
    dy = y1 - y0
    xi = 1
    if dx < 0:
        xi = -1
        dx = -dx
    D = (2 * dx) - dy
    x = x0
    for y in range(y0, y1+1):
        result[y] = x
        if D > 0:
            x = x + xi
            D = D + (2 * (dx - dy))
        else:
            D = D + 2*dx

def _get_line(result, x0, y0, x1, y1) -> None:
    if abs(y1 - y0) < abs(x1 - x0):
        if x0 > x1:
            _get_line_low(result, x1, y1, x0, y0)
        else:
            _get_line_low(result, x0, y0, x1, y1)
    else:
        if y0 > y1:
            _get_line_high(result, x1, y1, x0, y0)
        else:
            _get_line_high(result, x0, y0, x1, y1)


# Taken from: https://www.youtube.com/watch?v=hpiILbMkF9w
def _get_circle(lows, highs, cx, cy, r) -> None:
    assert isinstance(r, int), "TypeError"
    assert isinstance(cx, int), "TypeError"
    assert isinstance(cy, int), "TypeError"
    x, y = 0, -r
    p = 1 - 4*r
    while x < -y:
        if p > 0:
            y += 1
            p += 8*y
        p += 8*x + 4
        lows[cy+y] = cx-x
        lows[cy-y] = cx-x
        lows[cy+x] = cx-y
        lows[cy-x] = cx-y
        highs[cy+y] = cx+x
        highs[cy-y] = cx+x
        highs[cy+x] = cx+y
        highs[cy-x] = cx+y
        x += 1


class DrawImage:
    __Slots__ = "size", "pix", "image"

    def __init__(self, size:int) -> DrawImage:
        self.image:Image = Image.new("RGBA", (size,size), (0,0,0,0))
        self.pix = self.image.load()
        self.size:int = size

    def copy(self) -> DrawImage:
        new:DrawImage = DrawImage(self.size)
        new.image:Image = self.image.copy()
        new.pix = new.image.load()
        return new

    def crop_resize(self, show_size:int, inner_size:int) -> Image.Image:
        a = (self.size-inner_size)/2
        b = self.size-a
        img:Image.Image = self.image.crop((a, a, b, b))
        img:Image.Image = img.resize((show_size,show_size), Image.LANCZOS)
        return img

    def draw_circumference(self, pc, r1, r2, d, Δd, *, colour=WHITE, alpha=255):
        assert -360 <= d <= 360, "ValueError"
        assert 0 < Δd <= 360, "ValueError"
        assert r1 < r2, "ValueError"
        cx, cy = pc
        d %= 360
        for i in range(max(0,int(cx-r2)), min(self.size,int(cx+r2+1))):
            for j in range(max(0,int(cy-r2)), min(self.size,int(cy+r2+1))):
                if sq(i-cx)+sq(j-cy) < sq(r1):
                    continue
                if sq(i-cx)+sq(j-cy) > sq(r2):
                    continue
                if (i == cx) and (j == cy) and (r1 == 0):
                    fangle:float = d
                else:
                    # clockwise angle from top
                    fangle:float = (90+fatan(i-cx, j-cy))%360
                temp:bool = (d+Δd >= 360) and not \
                            ((fangle >= d) or (fangle <= (d+Δd)%360))
                if temp:
                    continue
                if (d+Δd < 360) and not (d <= fangle <= d+Δd):
                    continue
                self.pix[i,j] = colour+(alpha,)

    def draw_rectangle(self, x1, y1, x2, y2, *, colour=WHITE, alpha=255):
        for i in range(int(x1), int(x2+1)):
            for j in range(int(y1), int(y2+1)):
                self.pix[i,j] = colour+(alpha,)

    def draw_line(self, p1, p2, w, *, colour=WHITE, alpha=255) -> None:
        (x15,y15), (x35,y35) = p1, p2
        theta = fatan(x35-x15, y35-y15)
        x1, x2 = x15+w/2*sin(theta), x15-w/2*sin(theta)
        y1, y2 = y15-w/2*cos(theta), y15+w/2*cos(theta)
        x3, x4 = x35+w/2*sin(theta), x35-w/2*sin(theta)
        y3, y4 = y35-w/2*cos(theta), y35+w/2*cos(theta)
        self.draw_triangle((x1,y1), (x2,y2), (x3,y3), colour=colour,
                           alpha=alpha)
        self.draw_triangle((x2,y2), (x4,y4), (x3,y3), colour=colour,
                           alpha=alpha)
        # self.draw_polygon((x1,y1), (x2,y2), (x4,y4), (x3,y3), colour=colour,
        #                   alpha=alpha)

    def draw_rounded_line(self, p1, p2, w, *, colour=WHITE, alpha=255):
        (x1,y1), (x2, y2) = p1, p2
        self.draw_line((x1,y1), (x2,y2), w, colour=colour, alpha=alpha)
        self.draw_circle((x1,y1), w/2, colour=colour, alpha=alpha)
        self.draw_circle((x2,y2), w/2, colour=colour, alpha=alpha)

    def draw_triangle(self, p1, p2, p3, *, colour=WHITE, alpha=255):
        points1 = [-1]*self.size
        points2 = points1.copy()
        points3 = points1.copy()
        _get_line(points1, *map_int(*p1, *p2))
        _get_line(points2, *map_int(*p2, *p3))
        _get_line(points3, *map_int(*p3, *p1))
        self._draw_between_xs(points1, points2, points3, colour=colour,
                              alpha=alpha)

    def draw_circle(self, pc, r, *, colour=WHITE, alpha=255) -> None:
        lows, highs = [-1]*self.size, [-1]*self.size
        _get_circle(lows, highs, *map_int(*pc), int(r))
        self._draw_between_xs(lows, highs, colour=colour, alpha=alpha)

    def _draw_between_xs(self, *points, colour=WHITE, alpha=255) -> None:
        for y, xs in enumerate(zip(*points, strict=True)):
            xs = list(xs)
            while -1 in xs: xs.remove(-1)
            if xs:
                for x in range(min(xs), max(xs)+1):
                    self.pix[x,y] = colour+(alpha,)

    def draw_polygon(self, *ps:tuple[Point], colour=WHITE, alpha=255):
        first = lambda items: items[0]
        second = lambda items: items[1]
        minx, maxx = min(map(first, ps)), max(map(first, ps))
        miny, maxy = min(map(second, ps)), max(map(second, ps))
        for i in range(int(minx), int(maxx+1)):
            for j in range(int(miny), int(maxy+1)):
                if not self._in_polygon(ps, (i, j)):
                    continue
                self.pix[i,j] = colour+(alpha,)

    @staticmethod
    def _lines_from_verts(verts:tuple[Point]) -> Iterable[Line]:
        verts:list[Point] = list(verts)
        for a, b in zip(verts, [verts[-1]]+verts):
            yield a, b

    @staticmethod
    def _in_polygon(ps:tuple[Point], test:Point) -> bool:
        testx, testy = test
        c:int = 0 # Can be any size int even 1 bit
        for pointa, pointb in DrawImage._lines_from_verts(ps):
            pointax, pointay = pointa
            pointbx, pointby = pointb
            if (pointax == testx) and (pointay == testy):
                return True
            if (pointbx == testx) and (pointby == testy):
                return True
            if (pointay>testy) == (pointby>testy):
                continue
            if (testx < pointax < pointbx) or (testx < pointbx < pointax):
                c += 1
                continue
            if (pointax < pointbx < testx) or (pointbx < pointax < testx):
                continue
            gp:float = line_gradient(pointax, pointay, pointbx, pointby)
            x_intercept:float = (pointax-testx)-(pointay-testy)/gp
            if -ε < x_intercept < ε:
                return True
            if x_intercept > 0:
                c += 1
        return bool(c&1)


def draw_pause(a:int, b:int, c:int, d:int, size:int, bg:Colour) -> DrawImage:
    a, b, c, d = a/256*size, b/256*size, c/256*size, d/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), d, colour=bg)
    image.draw_rounded_line((a,b), (a,size-b), c, colour=WHITE)
    image.draw_rounded_line((size-a,b), (size-a,size-b), c, colour=WHITE)
    return image

def draw_plus(a:int, b:int, c:int, size:int, bg:Colour) -> DrawImage:
    a, b, c = a/256*size, b/256*size, c/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), c, colour=bg)
    image.draw_rounded_line((size>>1,a), (size>>1,size-a), b, colour=WHITE)
    image.draw_rounded_line((a,size>>1), (size-a,size>>1), b, colour=WHITE)
    return image

def draw_play(a:int, b:int, c:int, d:int, size:int, bg:Colour) -> DrawImage:
    if c is None:
        c:float = sqrt(3)/2*(256-2*b)+a
    a, b, c, d = a/256*size, b/256*size, c/256*size, d/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), d, colour=bg)
    image.draw_triangle((a,b), (a,size-b), (c,size>>1))
    #image.draw_triangle((size-a,size-b), (size-a,b), (size-c,size>>1))
    return image

def draw_restart(r1, r2, d1, d2, l, s, br, size, bg:Colour) -> DrawImage:
    r1, r2, s, br = r1/256*size, r2/256*size, s/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=bg)
    image.draw_circumference((size>>1,size>>1), r1, r2, d2, 360-d1-d2)
    cx, cy = size>>1, size>>1
    x1, y1 = cx-(r1-s)*sin(d1), cy-(r1-s)*cos(d1)
    x2, y2 = cx-(r2+s)*sin(d1), cy-(r2+s)*cos(d1)
    if l is None:
        l = sqrt(3)/2*sqrt(sq(x2-x1)+sq(y2-y1))
    else:
        l *= sqrt(3)/2*size/256
    g, s = div(x1-x2, y2-y1), sign(y1-y2)
    beta = l*sqrt(div(1, sq(g)+1))
    alpha = g*beta
    x3, y3 = (x1+x2)/2+beta, (y1+y2)/2+alpha
    image.draw_triangle((x1,y1), (x2,y2), (x3,y3))
    return image

def draw_x(r:int, w:int, br:int, size:int, bg:Colour) -> DrawImage:
    r, w, br = r/256*size, w/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=bg)
    d = (size>>1) - r/sqrt(2)
    image.draw_rounded_line((d,d), (size-d,size-d), w)
    image.draw_rounded_line((size-d,d), (d,size-d), w)
    return image

def draw_io(r1, r2, d, y1, y2, w, br, size, bg:Colour) -> DrawImage:
    r1, r2, w, br = r1/256*size, r2/256*size, w/256*size, br/256*size
    y1, y2 = y1/256*size, y2/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=bg)
    image.draw_circumference((size>>1,size>>1), r1, r2, d, 360-2*d,
                             colour=WHITE)
    image.draw_rounded_line((size>>1,y1), (size>>1,y2), w)
    return image

def draw_gear(n, r1, r2, ir1, ir2, or1, or2, br, size, fg, bg, reverse=False):
    r1, r2, ir1, ir2 = r1/256*size, r2/256*size, ir1/256*size, ir2/256*size
    or1, or2, br = or1/256*size, or2/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    centre = (size>>1,size>>1)
    image.draw_circle(centre, br, colour=bg)
    image.draw_circle(centre, or2, colour=fg)
    image.draw_circle(centre, or1, colour=bg)
    image.draw_circle(centre, ir2, colour=fg)
    image.draw_circle(centre, ir1, colour=bg)
    for i in range(n):
        if reverse:
            deg = (360/n*i+90)%360
        else:
            deg = (360/n*i-90)%360
        x, y = or2*cos(deg)+(size>>1), or2*sin(deg)+(size>>1)
        image.draw_circle((x,y), r1, colour=bg)
        image.draw_circle((x,y), r2, colour=fg)
        image.draw_circle((x,y), r1, colour=bg)
    image.draw_circumference(centre, or2, br, 0, 360, colour=bg)
    image.draw_circumference(centre, br, br*2, 0, 360, colour=fg, alpha=0)
    return image

def draw_exclam(y1, y2, w, r, br, size, bg:Colour) -> DrawImage:
    w, r, br = w/256*size, r/256*size, br/256*size
    y1, y2 = y1/256*size, y2/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=bg)
    image.draw_rounded_line((size>>1,y1), (size>>1,y2), w, colour=WHITE)
    image.draw_circle((size>>1,size-y1-r+w), r, colour=WHITE)
    return image

def draw_warning(s, y1, y2, y3, w, size, bg:Colour) -> DrawImage:
    y1, y2, y3 = y1/256*size, y2/256*size, y3/256*size
    s, w = s/256*size, w/256*size
    image:DrawImage = DrawImage(size)
    tx1 = (size-s)/2
    tx2 = size-tx1
    tx3 = (tx1+tx2)/2
    ty3 = tx1
    ty1 = ty2 = size-tx1
    ly1 = y1+ty3+w/2
    ly2 = y2+ty3-w/2
    image.draw_triangle((tx1,ty1), (tx2,ty2), (tx3,ty3), colour=bg)
    image.draw_rounded_line((size>>1,ly1), (size>>1,ly2), w, colour=BLACK)
    image.draw_circle((size>>1,y3+ty3+w/2), w/2, colour=BLACK)
    return image

def draw_test(size) -> DrawImage:
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), 100, colour=WHITE)
    image.draw_circumference((size>>1,size>>1), 0, 80, 90, 180, colour=BLACK)
    return image

def draw_tick(x1,y1, x2,y2, x3,y3, w, br, size, bg:Colour) -> DrawImage:
    x1, y1 = x1/256*size, y1/256*size
    x2, y2 = x2/256*size, y2/256*size
    x3, y3 = x3/256*size, y3/256*size
    br, w = br/256*size, w/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=bg)
    image.draw_rounded_line((x1,y1), (x2,y2), w, colour=WHITE)
    image.draw_rounded_line((x2,y2), (x3,y3), w, colour=WHITE)
    return image

# TODO
def draw_addon() -> Image.Image: ...

def draw_spinners(spinners_wanted:set[int], r:int, d:int, br:int,
                  size:int, bg:Colour) -> dict[str:list[Image.Image]]:
    _MAIN_COLOUR:Colour = bg
    _SUB_COLOUR:Colour = WHITE
    def name() -> str:
        if _MAIN_COLOUR == BLUE:
            return f"spinner{spinner}"
        elif _MAIN_COLOUR == BLACK:
            return f"spinner{spinner}-black"
        else:
            raise NotImplementedError()

    def circle_spinner(spinner:int, frames:tuple[list[int]]) -> None:
        # Helper for the spinners that are just blinking circles
        _frames:list[Image.Image] = []
        for frame in reversed(frames):
            img_cpy:DrawImage = image.copy()
            for pos, circle in enumerate(frame):
                if circle:
                    x:int = (size>>1) - d*(pos-1)
                    img_cpy.draw_circle((x,size>>1), r, colour=_SUB_COLOUR)
            _frames.append(img_cpy)
        sprites[name()] = _frames

    def line_spinner(spinner:int) -> None:
        # Helper for the spinners that are just lines
        _frames:list[Image.Image] = []
        for dir in reversed("|/-\\"):
            img_cpy:DrawImage = image.copy()
            x1, y2 = x2, y2 = (0, 0)
            if dir == "|":
                x1 = x2 = size>>1
                y1:int = (size>>1) - d
                y2:int = (size>>1) + d
            elif dir == "-":
                x1:int = (size>>1) - d
                x2:int = (size>>1) + d
                y1 = y2 = size>>1
            elif dir == "/":
                in_sqrt2:float = 1/sqrt(2)
                x1:int = (size>>1) - int(d*in_sqrt2)
                x2:int = (size>>1) + int(d*in_sqrt2)
                y1:int = (size>>1) - int(d*in_sqrt2)
                y2:int = (size>>1) + int(d*in_sqrt2)
            elif dir == "\\":
                in_sqrt2:float = 1/sqrt(2)
                x1:int = (size>>1) - int(d*in_sqrt2)
                x2:int = (size>>1) + int(d*in_sqrt2)
                y1:int = (size>>1) + int(d*in_sqrt2)
                y2:int = (size>>1) - int(d*in_sqrt2)
            img_cpy.draw_rounded_line((x1,y1), (x2,y2), r, colour=_SUB_COLOUR)
            _frames.append(img_cpy)
        sprites[name()] = _frames

    r, d, br = r/256*size, d/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=_MAIN_COLOUR)
    sprites:dict[str:list[Image.Image]] = dict()
    for spinner in spinners_wanted:
        if spinner == 1:
            circle_spinner(spinner, [(0,0,0), (1,0,0), (0,1,0), (0,0,1)])
        elif spinner == 2:
            circle_spinner(spinner,
                           [(0,0,0), (1,0,0), (1,1,0), (0,1,1), (0,0,1)])
        elif spinner == 3:
            circle_spinner(spinner,
                           [(0,0,0), (1,0,0), (1,1,0),
                            (1,1,1), (0,1,1), (0,0,1)])
        elif spinner == 4:
            circle_spinner(spinner, [(0,0,0), (0,0,1), (0,1,1), (1,1,1)])
            sprites[name()].append(sprites[name()][2])
            sprites[name()].append(sprites[name()][1])
        elif spinner == 5:
            circle_spinner(spinner, [(1,0,0), (0,1,0), (0,0,1)])
            sprites[name()].append(sprites[name()][1])
        elif spinner == 6:
            line_spinner(spinner)
        else:
            raise NotImplementedError()
    return sprites


ImageType:type = Image.Image | list[Image.Image]
TkImageType:type = ImageTk.PhotoImage | list[ImageTk.PhotoImage]
DisplayImgType:type = Callable[ImageTk.PhotoImage,None]

def init(*, size:int, compute_size:int=None, crop:bool=True,
         sprites_wanted:set[str]=ALL_SPRITE_NAMES) -> dict[str:ImageType]:
    size, show_size = (compute_size or size<<1), size
    inner_size:int = int(220/256*size)
    sprites:dict[str,DrawImage|list[DrawImage]] = dict()
    if "plus-black" in sprites_wanted:
        sprites["plus-black"] = draw_plus(88, 15, 100, size, bg=BLACK)
    if "plus-grey" in sprites_wanted:
        sprites["plus-grey"] = draw_plus(88, 15, 100, size, bg=DGREY)
    if "pause-green" in sprites_wanted:
        sprites["pause-green"] = draw_pause(108, 88, 15, 100, size, bg=DGREEN)
    if "pause-black" in sprites_wanted:
        sprites["pause-black"] = draw_pause(108, 88, 15, 100, size, bg=BLACK)
    if "play-green" in sprites_wanted:
        sprites["play-green"] = draw_play(95, 77, None, 100, size, bg=DGREEN)
    if "play-black" in sprites_wanted:
        sprites["play-black"] = draw_play(95, 77, None, 100, size, bg=BLACK)
    if "x-orange" in sprites_wanted:
        sprites["x-orange"] = draw_x(65, 15, 100, size, bg=ORANGE)
    # if "close2" in sprites_wanted:
    #     sprites["close2"] = draw_close2(65, 15, 100, size)
    if "restart" in sprites_wanted:
        sprites["restart"] = draw_restart(50, 65, 50, 40, None, 15, 100,
                                          size, bg=ORANGE)
    if "restart-blue" in sprites_wanted:
        sprites["restart-blue"] = draw_restart(50, 65, 50, 40, None, 15, 100,
                                               size, bg=BLUE)
    if "restart-black" in sprites_wanted:
        sprites["restart-black"] = draw_restart(50, 65, 50, 40, None, 15, 100,
                                                size, bg=BLACK)
    if "io-red" in sprites_wanted:
        sprites["io-red"] = draw_io(50, 65, 40, 65, 130, 15, 100, size, bg=RED)
    if "gear-white" in sprites_wanted:
        sprites["gear-white"] = draw_gear(6, 15, 30, 15, 30, 60, 75, 100,
                                          size, fg=BLACK, bg=WHITE)
    if "gear-grey" in sprites_wanted:
        sprites["gear-grey"] = draw_gear(6, 15, 30, 15, 30, 60, 75, 100,
                                         size, fg=WHITE, bg=DGREY)
    if "warning" in sprites_wanted:
        sprites["warning"] = draw_warning(180, 62, 128, 144, 16,
                                          size, bg=DYELLOW)
    if "exclam-blue" in sprites_wanted:
        sprites["exclam-blue"] = draw_exclam(75, 135, 20, 15, 100,
                                             size, bg=BLUE)
    if "exclam-orange" in sprites_wanted:
        sprites["exclam-orange"] = draw_exclam(75, 135, 20, 15, 100,
                                               size, bg=ORANGE)
    if "exclam-red" in sprites_wanted:
        sprites["exclam-red"] = draw_exclam(75, 135, 20, 15, 100,
                                               size, bg=RED)
    if "i-red" in sprites_wanted:
        sprites["i-red"] = draw_exclam(185, 125, 20, 15, 100, size, bg=RED)
    if "i-orange" in sprites_wanted:
        sprites["i-orange"] = draw_exclam(185, 125, 20, 15, 100, size,
                                          bg=ORANGE)
    if "i-blue" in sprites_wanted:
        sprites["i-blue"] = draw_exclam(185, 125, 20, 15, 100, size, bg=BLUE)
    if "i-black" in sprites_wanted:
        sprites["i-black"] = draw_exclam(185, 125, 20, 15, 100, size, bg=BLACK)
    if "tick-green" in sprites_wanted:
        sprites["tick-green"] = draw_tick(75,145, 110,180, 190,100,
                                          15, 100, size, bg=DGREEN)
    if "tick-black" in sprites_wanted:
        sprites["tick-black"] = draw_tick(75,145, 110,180, 190,100,
                                          15, 100, size, bg=BLACK)
    if "x-red" in sprites_wanted:
        sprites["x-red"] = draw_x(65, 15, 100, size, bg=RED)
    if any(name.startswith("spinner") for name in sprites_wanted):
        spinners_wanted:set[int] = set()
        colours:set[Colour] = set()
        for name in sprites_wanted:
            number, *colour = name.removeprefix("spinner").split("-",1)
            spinners_wanted.add(int(number))
            if not colour: colour:list[str] = [""]
            colours.add(BLACK if colour[0] == "black" else BLUE)
        for colour in colours:
            sprites.update(draw_spinners(spinners_wanted, 25, 60, 100, size,
                                         bg=colour))
    ret:dict[str:ImageType] = dict()
    for name in sprites_wanted:
        draws:DrawImage|list[DrawImage] = sprites[name]
        if not isinstance(draws, list):
            draws:list[DrawImage] = [draws]
        imgs:list[Image.Image] = [None]*len(draws)
        for i, draw in enumerate(draws):
            if crop:
                imgs[i] = draw.crop_resize(show_size, inner_size)
            else:
                imgs[i] = draw.image
        ret[name] = imgs if len(imgs)>1 else imgs[0]
    return ret


class SpriteCache:
    __slots__ = "_sprites", "size", "compute_size"

    def __init__(self, *, size:int, compute_size:int=None) -> SpriteCache:
        self._sprites:dict[str:Image.Image] = dict()
        self.compute_size:int = compute_size
        self.size:int = size

    def __getitem__(self, name:str) -> ImageType:
        if name not in ALL_SPRITE_NAMES:
            raise KeyError(f"Unknown sprite {name=!r}")
        if name not in self._sprites:
            self._sprites[name] = init(size=self.size, sprites_wanted={name},
                                       compute_size=self.compute_size)[name]
        return self._sprites[name]


class GifDisplay:
    __slots__ = "delay", "_func", "_cache", "_afterid", "_curr"

    def __init__(self, _func:DisplayImgType, delay:int, cache:TkSpriteCache):
        self._curr:list[ImageTk.PhotoImage] = []
        self._cache:TkSpriteCache = cache
        self._func:DisplayImgType = _func
        self._afterid:str|None = None
        self.delay:int = delay

    def change(self, name:str) -> GifDisplay:
        self._curr:list[ImageTk.PhotoImage] = self._cache[name]
        return self

    def start(self) -> GifDisplay:
        if self._afterid is None:
            assert len(self._curr), "No gif set"
            self._next()
        return self

    def stop(self) -> GifDisplay:
        if self._afterid is not None:
            self._cache._master.after_cancel(self._afterid)
            self._afterid:str|None = None
        return self

    def _next(self, i:int=0) -> None:
        i %= len(self._curr)
        self._func(self._curr[i])
        self._afterid = self._cache._master.after(self.delay, self._next, i+1)


class TkSpriteCache:
    __slots__ = "_master", "_sprites", "_tksprites"

    def __init__(self, master:tk.Misc, *, size:int, compute_size:int=None):
        assert isinstance(master, tk.Misc), "TypeError"
        self._tksprites:dict[str:TkImageType] = dict()
        self._sprites:SpriteCache = SpriteCache(compute_size=compute_size,
                                                size=size)
        self._master:tk.Misc = master

    def __getitem__(self, name:str) -> TkImageType:
        if name not in self._tksprites:
            imgs:ImageType = self._sprites[name]
            if not isinstance(imgs, list):
                imgs:ImageType = [imgs]
            tkimgs:TkImageType = [None]*len(imgs)
            for i, img in enumerate(imgs):
                tkimgs[i] = ImageTk.PhotoImage(img, master=self._master)
            self._tksprites[name] = tkimgs if len(tkimgs) != 1 else tkimgs[0]
        return self._tksprites[name]

    def display_gif(self, name:str, delay:int,
                    display:DisplayImgType) -> GifDisplay:
        gif_display:GifDisplay = GifDisplay(display, delay, self)
        gif_display.change(name)
        return gif_display


if __name__ == "__main__":
    size:int = 256>>1
    wanted:set[str] = {"gear-grey",
                       "warning",
                       "x-red",
                       "plus-grey",
                       "restart",
                       "i-red",
                       "tick-green", "tick-black",}

    root = tk.Tk()
    root.geometry("+0+0")
    root.resizable(False, False)
    sprites:TkSpriteCache = TkSpriteCache(root, size=size)

    start:float = perf_counter()
    print(f"[DEBUG]: Overall: {perf_counter()-start:.2f} seconds")

    labels = []
    for i, name in enumerate(sorted(wanted)):
        image = sprites[name]
        im = tk.Label(root, bd=0, highlightthickness=0, bg="black", image=image)
        im.grid(row=0, column=i)
        im.bind("<Button-1>", lambda e: print(e.x*256//size, e.y*256//size))
        label = tk.Label(root, text=name, bg="black", fg="white")
        label.grid(row=1, column=i, sticky="ew")

    root.mainloop()


if __name__ == "__main__":
    DELAY:int = 850 # milliseconds
    size:int = 256>>1
    wanted:set[str] = {"spinner1", "spinner2", "spinner3", "spinner4",
                       "spinner5", "spinner6", "spinner6-black"}

    root = tk.Tk()
    root.geometry("+0+0")
    root.resizable(False, False)
    sprites:TkSpriteCache = TkSpriteCache(root, size=size)

    def save_as_gif(name:str, filename:str) -> None:
        frames:list[Image.Image] = SpriteCache(size=size)[name]
        # If transparent: disposal=2
        # loop=0 means loop forever
        frames[0].save(filename, save_all=True, append_images=frames[1:],
                       duration=DELAY, loop=0, format="gif")

    for i, name in enumerate(sorted(wanted)):
        start:float = perf_counter()

        im = tk.Label(root, bd=0, highlightthickness=0, bg="black")
        im.grid(row=0, column=i)
        im.bind("<Button-1>", lambda e: print(e.x*256//size, e.y*256//size))
        label = tk.Label(root, text=name, bg="black", fg="white")
        label.grid(row=1, column=i, sticky="ew")
        set_image_callback = lambda img, im=im: im.config(image=img)
        gif:GifDisplay = sprites.display_gif(name, DELAY, set_image_callback)
        gif.start()

        print(f"[DEBUG]: {name!r}: {perf_counter()-start:.2f} seconds")

        from os import path
        if path.exists("spinners/"):
            save_as_gif(name, f"spinners/{name}.gif")

    root.mainloop()
