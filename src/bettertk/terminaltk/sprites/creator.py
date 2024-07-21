from __future__ import annotations
from math import pi, sqrt, sin as _sin, cos as _cos, tan as _tan, atan as _atan
from PIL import Image, ImageTk
from time import perf_counter
import tkinter as tk


ε:float = 0.01
DEBUG:bool = False
BLACK:tuple[int,int,int] = (0,0,0)
WHITE:tuple[int,int,int] = (255,255,255)
RED:tuple[int,int,int] = (255,0,0)
GREEN:tuple[int,int,int] = (0,255,0)
BLUE:tuple[int,int,int] = (0,0,255)
CYAN:tuple[int,int,int] = (0,256,256)
DGREEN:tuple[int,int,int] = (0,180,0)
YELLOW:tuple[int,int,int] = (255,255,0)
ORANGE:tuple[int,int,int] = (255,165,0)
DYELLOW:tuple[int,int,int] = (252,225,0)
sin:Function[float,float] = lambda deg: _sin(deg/180*pi)
cos:Function[float,float] = lambda deg: _cos(deg/180*pi)
tan:Function[float,float] = lambda deg: _tan(deg/180*pi)
atan:Function[float,float] = lambda x: _atan(x)/pi*180
sq:Function[float,float] = lambda x: x*x
sign:Function[float,float] = lambda x: (2*(x>0)-1)*(x!=0)
line_gradient:Function = lambda x1,y1,x2,y2: div(y2-y1, x2-x1)
is_bellow_line = lambda p1,g,p2: p2[1]+g*(p1[0]-p2[0]) < p1[1]
is_above_line = lambda p1,g,p2: not is_bellow_line(p1,g,p2)
is_right_line = lambda p1,g,p2: p1[0]>p2[0]
is_left_line = lambda p1,g,p2: not is_right_line(p1,g,p2)
div:Function[float,float,float] = lambda a,b: (a/ε if b == 0 else a/b)
def fatan(x:float, y:float) -> float:
    assert not (x == y == 0), "Fatan of (0,0) doesn't exist"
    if x == 0:
        return 270-180*(y>0)
    if x < 0:
        return atan(y/x)+180
    return atan(y/x)%360


def triangle_order_left(p1, p2) -> ((int,int), (int,int)):
    # Order right, prefer top
    if p1[0] < p2[0]:
        return p1, p2
    if p2[0] < p1[0]:
        return p2, p1
    if p1[1] < p2[1]:
        return p1, p2
    assert p1[1] > p2[1], "2 Points are the same"
    return p2, p1

def triangle_order_top(p1, p2) -> ((int,int), (int,int)):
    # Oder top, prefer <useless>
    if p1[1] < p2[1]:
        return p1, p2
    if p1[1] > p2[1]:
        return p2, p1
    if p1[0] < p2[0]:
        return p1, p2
    assert p1[0] > p2[0], "2 Points are the same"
    return p2, p1

def triangle_order(p1, p2, p3) -> tuple[int*6]:
    p1, p2 = triangle_order_left(p1, p2)
    p1, p3 = triangle_order_left(p1, p3)
    p2, p3 = triangle_order_top(p2, p3)
    if p1[0] == p2[0]:
        if p3[0] > p2[0]:
            p2, p3 = p3, p2
    elif p1[0] == p3[0]:
        if p2[0] < p3[0]:
            p2, p3 = p3, p2
    elif line_gradient(*p1, *p2) > line_gradient(*p1, *p3):
        p2, p3 = p3, p2
    return (p1, p2, p3)


class DrawImage:
    __Slots__ = "size", "pix", "image"

    def __init__(self, size:int) -> DrawImage:
        self.image:Image = Image.new("RGBA", (size,size), (0,0,0,0))
        self.pix = self.image.load()
        self.size:int = size

    def crop_resize(self, show_size:int, inner_size:int) -> Image.Image:
        a = (self.size-inner_size)/2
        b = self.size-a
        img:Image.Image = self.image.crop((a, a, b, b))
        img:Image.Image = img.resize((show_size,show_size), Image.LANCZOS)
        return img

    def draw_circle(self, pc, r, **kwargs) -> None:
        self.draw_circumference(pc, 0, r, 0, 360, **kwargs)

    def draw_circumference(self, pc, r1, r2, d, Δd, *, colour=WHITE, alpha=256):
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
                if (d+Δd >= 360) and not ((fangle >= d) or (fangle <= (d+Δd)%360)):
                    continue
                if (d+Δd < 360) and not (d <= fangle <= d+Δd):
                    continue
                self.pix[i,j] = colour+(alpha,)

    def draw_rectangle(self, x1, y1, x2, y2, *, colour=WHITE, alpha=256) -> None:
        for i in range(int(x1), int(x2+1)):
            for j in range(int(y1), int(y2+1)):
                self.pix[i,j] = colour+(alpha,)

    def draw_line(self, p1, p2, w, *, colour=WHITE, alpha=256) -> None:
        (x15,y15), (x35,y35) = p1, p2
        theta = fatan(x35-x15, y35-y15)
        x1, x2 = x15+w/2*sin(theta), x15-w/2*sin(theta)
        y1, y2 = y15-w/2*cos(theta), y15+w/2*cos(theta)
        x3, x4 = x35+w/2*sin(theta), x35-w/2*sin(theta)
        y3, y4 = y35-w/2*cos(theta), y35+w/2*cos(theta)
        self.draw_triangle((x1,y1), (x2,y2), (x3,y3), colour=colour, alpha=alpha)
        self.draw_triangle((x2,y2), (x4,y4), (x3,y3), colour=colour, alpha=alpha)
        # self.draw_polygon((x1,y1), (x2,y2), (x4,y4), (x3,y3), colour=colour,
        #                   alpha=alpha)

    def draw_rounded_line(self, p1, p2, w, *, colour=WHITE, alpha=256):
        (x1,y1), (x2, y2) = p1, p2
        self.draw_line((x1,y1), (x2,y2), w, colour=colour, alpha=alpha)
        self.draw_circle((x1,y1), w/2, colour=colour, alpha=alpha)
        self.draw_circle((x2,y2), w/2, colour=colour, alpha=alpha)

    def draw_triangle(self, p1, p2, p3, *, colour=WHITE, alpha=256):
        (x1,y1), (x2,y2), (x3,y3) = triangle_order(p1, p2, p3)
        g1:float = line_gradient(x1, y1, x2, y2)
        g2:float = line_gradient(x3, y3, x2, y2)
        g3:float = line_gradient(x1, y1, x3, y3)
        for i in range(int(min(x1,x2,x3)), int(max(x1,x2,x3)+1)):
            for j in range(int(min(y1,y2,y3)), int(max(y1,y2,y3)+1)):
                # Bellow[p1,p2]
                if not is_bellow_line((i,j), g1, (x1,y1)):
                    continue
                # Bellow[p2,p3] if x2 < x3 else above[p2,p3]
                if x2 < x3:
                    if not is_bellow_line((i,j), g2, (x2,y2)):
                        continue
                elif x2 == x3:
                    if not is_left_line((i,j), g3, (x2,y2)):
                        continue
                else:
                    if not is_above_line((i,j), g2, (x2,y2)):
                        continue
                # Above[p1,p3] if x1 < x3 else bellow[p1,p3]
                if x1 < x3:
                    if not is_above_line((i,j), g3, (x3,y3)):
                        continue
                elif x1 == x3:
                    if not is_right_line((i,j), g3, (x3,y3)):
                        continue
                else:
                    if not is_bellow_line((i,j), g3, (x3,y3)):
                        continue
                self.pix[i,j] = colour+(alpha,)
        #self.draw_circle((x1,y1), 3, colour=RED)
        #self.draw_circle((x2,y2), 3, colour=GREEN)
        #self.draw_circle((x3,y3), 3, colour=BLUE)

    def draw_polygon(self, *ps:tuple[Point], colour=WHITE, alpha=256):
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


def draw_pause(a:int, b:int, c:int, d:int, size:int) -> DrawImage:
    a, b, c, d = a/256*size, b/256*size, c/256*size, d/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), d, colour=DGREEN)
    image.draw_rounded_line((a,b), (a,size-b), c, colour=WHITE)
    image.draw_rounded_line((size-a,b), (size-a,size-b), c, colour=WHITE)
    return image

def draw_play(a:int, b:int, c:int, d:int, size:int) -> DrawImage:
    if c is None:
        c:float = sqrt(3)/2*(256-2*b)+a
    a, b, c, d = a/256*size, b/256*size, c/256*size, d/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), d, colour=DGREEN)
    image.draw_triangle((a,b), (a,size-b), (c,size>>1))
    #image.draw_triangle((size-a,size-b), (size-a,b), (size-c,size>>1))
    return image

def draw_restart(r1, r2, d1, d2, l, s, br, size:int) -> DrawImage:
    r1, r2, s, br = r1/256*size, r2/256*size, s/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=ORANGE)
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

def draw_close(r:int, w:int, br:int, size:int) -> DrawImage:
    """ Same as draw_error but with ORANGE instead of RED """
    r, w, br = r/256*size, w/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=ORANGE)
    d = (size>>1) - r/sqrt(2)
    image.draw_rounded_line((d,d), (size-d,size-d), w)
    image.draw_rounded_line((size-d,d), (d,size-d), w)
    return image

def draw_kill(r1, r2, d, y1, y2, w, br, size) -> DrawImage:
    r1, r2, w, br = r1/256*size, r2/256*size, w/256*size, br/256*size
    y1, y2 = y1/256*size, y2/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=RED)
    image.draw_circumference((size>>1,size>>1), r1, r2, d, 360-2*d, colour=WHITE)
    image.draw_rounded_line((size>>1,y1), (size>>1,y2), w)
    return image

def draw_settings(n, r1, r2, ir1, ir2, or1, or2, br, size, reverse=False) -> DrawImage:
    r1, r2, ir1, ir2 = r1/256*size, r2/256*size, ir1/256*size, ir2/256*size
    or1, or2, br = or1/256*size, or2/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=WHITE)
    image.draw_circumference((size>>1,size>>1), or1, or2, 0, 360, colour=BLACK)
    image.draw_circumference((size>>1,size>>1), ir1, ir2, 0, 360, colour=BLACK)
    for i in range(n):
        if reverse:
            deg = (360/n*i+90)%360
        else:
            deg = (360/n*i-90)%360
        x, y = or2*cos(deg)+(size>>1), or2*sin(deg)+(size>>1)
        image.draw_circle((x,y), r1, colour=WHITE)
        image.draw_circumference((x,y), r1, r2, 0, 360, colour=BLACK)
    image.draw_circumference((size>>1,size>>1), or2, br, 0, 360, colour=WHITE)
    image.draw_circumference((size>>1,size>>1), br, br*2, 0, 360, colour=BLACK, alpha=0)
    return image

def draw_stop(y1, y2, w, r, br, size) -> DrawImage:
    """ Same as draw_info but with ORANGE instead of BLUE """
    w, r, br = w/256*size, r/256*size, br/256*size
    y1, y2 = y1/256*size, y2/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=ORANGE)
    image.draw_rounded_line((size>>1,y1), (size>>1,y2), w, colour=WHITE)
    image.draw_circle((size>>1,size-y1-r+w), r, colour=WHITE)
    return image

def draw_warning(s, y1, y2, y3, w, size) -> DrawImage:
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

    image.draw_triangle((tx1,ty1), (tx2,ty2), (tx3,ty3), colour=DYELLOW)
    image.draw_rounded_line((size>>1,ly1), (size>>1,ly2), w, colour=BLACK)
    image.draw_circle((size>>1,y3+ty3+w/2), w/2, colour=BLACK)
    return image

def draw_info(y1, y2, w, r, br, size) -> DrawImage:
    """ Same as draw_stop but with BLUE instead of ORANGE """
    w, r, br = w/256*size, r/256*size, br/256*size
    y1, y2 = y1/256*size, y2/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=BLUE)
    image.draw_rounded_line((size>>1,y1), (size>>1,y2), w, colour=WHITE)
    image.draw_circle((size>>1,size-y1-r+w), r, colour=WHITE)
    return image

def draw_error(r:int, w:int, br:int, size:int) -> DrawImage:
    """ Same as draw_close but with RED instead of ORANGE """
    r, w, br = r/256*size, w/256*size, br/256*size
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), br, colour=RED)
    d = (size>>1) - r/sqrt(2)
    image.draw_rounded_line((d,d), (size-d,size-d), w)
    image.draw_rounded_line((size-d,d), (d,size-d), w)
    return image

def draw_test(size) -> DrawImage:
    image:DrawImage = DrawImage(size)
    image.draw_circle((size>>1,size>>1), 100, colour=WHITE)
    image.draw_circumference((size>>1,size>>1), 0, 80, 90, 180, colour=BLACK)
    return image

def draw_addon() -> Image.Image: ...


ALL_SPRITE_NAMES:set[str] = {"pause", "play", "stop", "close", "restart",
                             "kill", "settings", "warning", "info", "error"}
#ALL_SPRITE_NAMES = {"warning", "info", "error"}

def init(size:int, show_size:int, inner_size:int,
         sprites_wanted:set[str]=ALL_SPRITE_NAMES) -> dict[str:Image.Image]:
    inner_size:int = int(inner_size/256*size)
    sprites:dict[str,Image.Image] = dict()
    start:float = perf_counter()
    if "pause" in sprites_wanted:
        sprites["pause"] = draw_pause(108, 88, 15, 100, size)
    if "play" in sprites_wanted:
        sprites["play"] = draw_play(95, 77, None, 100, size)
    if "stop" in sprites_wanted:
        sprites["stop"] = draw_stop(75, 135, 20, 15, 100, size)
    if "close" in sprites_wanted:
        sprites["close"] = draw_close(65, 15, 100, size)
    if "close2" in sprites_wanted:
        sprites["close2"] = draw_close2(65, 15, 100, size)
    if "restart" in sprites_wanted:
        sprites["restart"] = draw_restart(50, 65, 50, 40, None, 15, 100, size)
    if "kill" in sprites_wanted:
        sprites["kill"] = draw_kill(50, 65, 40, 65, 130, 15, 100, size)
    if "settings" in sprites_wanted:
        sprites["settings"] = draw_settings(6, 15, 30, 15, 30, 60, 75, 100, size)
    if "warning" in sprites_wanted:
        sprites["warning"] = draw_warning(180, 62, 128, 144, 16, size)
    if "info" in sprites_wanted:
        sprites["info"] = draw_info(75, 135, 20, 15, 100, size)
    if "error" in sprites_wanted:
        sprites["error"] = draw_error(65, 15, 100, size)
    sprites = {name:img.crop_resize(show_size, inner_size) for name,img in sprites.items()}
    if DEBUG: print(f"[DEBUG]: Overall: {perf_counter()-start:.2f} seconds")
    return sprites


class SpritesCache:
    __slots__ = "sprites", "args"

    def __init__(self, size:int, show_size:int, inner_size:int) -> SpritesCache:
        self.args:tuple[int,int,int] = (size, show_size, inner_size)
        self.sprites:dict[str:Image.Image] = dict()

    def __getitem__(self, key:str) -> Image.Image|None:
        if key not in ALL_SPRITE_NAMES:
            return None
        if key not in self.sprites:
            self.sprites[key] = init(*self.args, {key})[key]
        return self.sprites[key]


if __name__ == "__main__":
    DEBUG:bool = True
    size:int = 256
    wanted:set[str] = {"info", "play", "close", "warning", "error", "kill"}
    sprites:dict[str:Image.Image] = init(size, size>>1, 220, wanted)

    root = tk.Tk()
    root.geometry("+0+0")
    root.resizable(False, False)

    tksprites = {name:ImageTk.PhotoImage(img) for name,img in sprites.items()}

    labels = []
    for i, name in enumerate(wanted):
        image = tksprites[name]
        im = tk.Label(root, bd=0, highlightthickness=0, bg="black", image=image)
        im.grid(row=0, column=i)
        im.bind("<Button-1>", lambda e: print(e.x, e.y))
        label = tk.Label(root, text=name, bg="black", fg="white")
        label.grid(row=1, column=i, sticky="ew")