from __future__ import annotations
from traceback import format_exception, format_exc
import tkinter as tk
import traceback
import os

PATH:str = os.path.abspath(os.path.dirname(__file__))
ERR_PATH_FOLDER:str = os.path.join(PATH, "error_logs")
ERR_PATH_FORMAT:str = os.path.join(ERR_PATH_FOLDER, "error.%i.txt")

i:int = 0
while True:
    err_path:str = ERR_PATH_FORMAT%i
    if not os.path.exists(err_path):
        break
    try:
        with open(err_path, "rb") as file:
            if file.read(1) == b"":
                break
    except: ...
    i += 1


HasErrorer:type = bool
BUTTON_KWARGS:dict = dict(activeforeground="white", activebackground="grey",
                          bg="black", fg="white", highlightthickness=0,
                          takefocus=False)
ERROR_IMG_DATA:str = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x80\x00\x00\x00\x80\x08\x06\x00\x00\x00\xc3>a\xcb\x00\x00\x12\x19IDATx\x9c\xed\x9di\xac$\xd5u\xc7\x7f\xd5\xef\xf5\x0c[\xc2\xc4\x96\x1dV{<\x0b\x868v\x12$\x90\x1c\xb1\x98\x1d\x9c\x89P\x8c\x159\xb1\x84e)a\x19\x03F\x8eP\x12;A \x05)\x96\xf8`\xb6\xd9\x12\x81!@b%Ql\x12B,;\x1a\xb6abG&\x8a\x81\x10\x08(\x98\xddv\x06\x0f0o\x86\xb7\xf5?\x1f\xce=\xd4}=\xbdTuU\xbf\xae\xea\xe9#\x1d\xf5{\xd5]U\xf7\xde\xf3?\xe7\x9es\xeb\x9eS0\xa1\tMhB\x13\x9a\xd0\x81I\x82d\xd4m\x18%\x8de\xe7#\xa1&\xc0T\x8f\x9f\xb6\x12X\x144{_\x8eE\xff\'\xb1\xff\'T5\x12L\x0b\x9a\x82\xe9\x9c\xe7\x1d\x9e\xf3\xf7\xcdp\xaf^\xc0\xaa\r\xd5\xd6\x02D\x02h\xc1R\xcd\x14\xac\xb2\x0f\xde\x0f\\\xd3\xe1\xf4$|\x7f8\xf0Q\xe0Q\xa0\xe1\xd7J/C\x02\xfc\x0f\xb0\r\xbb\xdf\x9bId\r"K\xd3\x00\x94,=\xbf\x16T+\x00\xc8\x06\xda\x07{\xb1\xed\xbbK\x81\x95\xc0a\xc0\x97\xb1\xbe5\xe9m\xde\xb3\xd2\x1e\x0c\x00\xff\x01\xfcu\xb8\xe6\xbf%\xb0\xb3\xad\r\xd3\x18\x08T\x97\xa9\xa2\x16\x00\x08\x03\x9b$0\x1f\x1d;\x13\xd3\xde\xcb\xed_\x8e\xefr\xfaB\x9f\xcb\xb7k~\xa7\xef\x1b\x1d\x8e\xcf\x02/\x00?\x05\xae\x07^H\xe0\xb9\xa8}M`\xa1.@\xa8$\xb5\xcf\xe7\x82c\x047\x0b\xfeE\xa06\x9e\x17\xcc\x05nE\xdc\xfe\xbbA\xd8\xaf\xb5\x18\xdd\xa3\xfd7?\x11|K\xf0\xdb2K\xe4mn\xa83\x80*A\x95\xb3\x00a^}wN\r\xff\x7f\x0e8\x01\xb8\x028$\xfc\xd4\xa7\x80x\x1e^N\x12\xa9v\xb7X\n\xd6\x9d\xc0C\xc0_%\xf0_\xe1\xc7S\xd4\xd4OX6j\xf7\xac\x05\x9f\x11<\xd9\xa6i\x0b\x81\xcb\xd0\xec2\xb9\x15\xda\x15[\x9d\xb7\x05[\x04\'F}j\xaa\x82\x8a7R\x8a\x07$\x84X\x17\n\xfe=\x1aH7\xbd\xa3\x16rVno\xef\x8c\xe0\x1e\x99\xcf\xb2_\x9f\x0fhr\xad\x17\xac\x14|V\xf0H4p\xf3a0G-\xd0\xa2V!>\xf6u\xc1\x9a\xd0\xe7J\xfb\x07C\xa5\xd0\xf9f\xf8\xfb(\xc1\x0f\xa2AZ\xa8\xb9\xe0\xfb\x01a^\x169\xf8X\xe4Z\xbc\xaa=)\x8a\xcd\x05\xd7\xcb<h7\x9dU\x9c\xdf\xcb\xe4\xf9\xe8\xef\xa7\x04\x1f\t\xe30\xa51Y]\xecIJM\xfe\xc7\x04\xdf\x89\x06c\x9c4>\x0b;\xd0\x7f"\xb8\xb9}|\xc6\x8e\x04\x89\x82\xe3#\xf8S\xc1k\x91F\x94\x15\xaf\xd7\x8dc\xd0\xdf\'8?\x8cO\x19\xab\x97\xd5!E\xe6Mpw\xd4\xe9\xf9!\x0cj\xdd\xb8\xd56\x0e\x17\x84qZ\xa9q\x88\x14\x14\x994\xc1\x9d\xa1\x93\xb3:p\xb5\xbe\x1b{\xc43\'\xd8\x10\x8dY}A\xa0\xe0\xdd\n~C\xf0\xafQGG=\xd8UeW\x8aw\x04\x7f!88\x8c_\xfd\xfc\x02\xa5!\xde\xf9J\x1d\x9eq\xf7\xf0\xcb\x02\x81\x03\xe1\x11\xd9\xd3M\x7f\x12Z:\r\xe5\xa2\x82fb\x9a\xfeI\xe0\xfep\x9f\x05\xea\x88\xe4\xe5\xa7$\xf0\x1cp\np\x7f\x00\x81\x86\x01\x82\xd2\xe7\x97H\xf8\x1b\x80\xbf\']\xe480W\xbc\x8a\xd1<fI\x1f\x05\xceN\xccwj\x94\xf9@\xa9T\x00\x08\xa6\xc2\x1e\xbb\xf3\x81\xfb0\xe1\x8b\x89\xf0\x8b\xd0\x026\x8e;1\x10\xec\x95\xed\x8dP\x19\x17/\r\x00\xc1Qi\x01\xe7\x01\x0f\xd8\xa1\x89\xf0K"\x07\xc1\xc3\xc0o\x02\xfb(i\xb3I)\xc2Q\x98\xb7B\x83\xae\r\x87\x17\xcb\xba\xfe\x84\x98\xc6|\x82\xd3\x80\rI:5\x14\xa6\xc2\x02\x8a\x84\xbf \xb8\x0b\xf88&\xfc\x03\xeb\x01\xc7\xf0\xa9\x89\t\xfe/e \x98+\xc3),<\x05(\xec\xd7\x03\xee\x00>Kj\xae&T>\xb9\xc9oaN\xf6w\x08\xca7\xe8\x05\x0b\x01 \xf2\xf8\xff\x10\xf8sl\xa3\xe4\xca>\xa7M\xa8\x18\xb5\x08[\xe6\x80\xf7%\xb0\xabHd0\xb0\t\t\xe6\xa7%\xdb\xee\xf4E\x0c\x85+\x06\xbd\xde\x842S\x03\x9bb\x13\xe0F\xc1\xa1\xd8\xb3\x96\x81\x94y`\x0b\x10i\xff\x83\xc0\xe9\x94a\xfa\xa7\xa6l\xb9\xe3\xdd\xd6%\xb0\xb8\xd8\xfd\xf7u\xa0F#\xb8\xc7m\x0e{\xabp(\xef\x8e\xe0o%\xf0M\xc1\xf4 S\xc1@\x00\x88\xe2\xfd\xeb\xb0$\x0c(\xea\x95v\x1a\xa4^\xc7\xeb@\x8dFwA\xf7\xfa.\x1b\t\x13\xf8\x8f\x81s\x80g\x01\xf2N\x05\xb9\xa7\x80`\xfa%x/\xf0%L\xeb\x8b;}\x12\x9cq\x06\xec\xd8\x01O>\t\xdf\xff>\x9c{\xae\x1dO\x12\xe3:\xd1\xd4\x94\t\xf8\x98c\xe0+_\x81\x1f\xfe\x10\x9ex\x02n\xbc\x11\xd6\xaf\xb7\xef\x8a\xf5\xc9O>\x06\xb8&\x08~\xf8K\xed\xb2\xf9\xa6\xa1t\xbbv\xb1\x07<SS\xd2\xca\x95\xd2W\xbf\xaa\x8e\xb4i\x93\xfd\xae\xd9\x94\x92d\xd4\x0fj\xb2\xf1\xf4\xb4}\xae_/\xbd\xf2\xca\xfe}\xda\xbd[:\xe5\x14\xebO\xa3Q\xf4~\xfet\xf5\x0bA>\xc3\x8b\xc0\x94n\xea\xf8ti\xc2\x07\xe9\x8c3l`\xf6\xed\x93\x16\x16\xa4\xc5E\xe3w\xde\xb1\xe3[\xb6\xa4\xbf\xaf:\x08\\\xf8\xc7\x1d\'\xfd\xe8G\xd6\xfe\xb9\xb9\xb4Ossv\xec\x99g\xecw\xc5\x01\xe0\xfb(\x9f\x11\xac\x92m\xab/\xdf\\\xca\xb6tM\x0b\x0e\x95\xed\xd9/\xbe\x81\xd3;\xbfcG:@\xed\xe4\x03\xb6uk\xf5A\xe0\xc2_\xbdZz\xf1Ek\xf7\xfc\xfc\xfe}\x9a\x9d\xb5~]|\xf1\xd2\xf3\x06g\x97\xc3\xa5\xb1\xa2\x96\r\x00\xd7\xfeO\xb5\xdd\xb48\x00\x9e}\xd6\x06\xa6\x13\x00\xe2A\xf4\xe9`z\xbaz p!\xae]+\xbd\xf6\x9a\xb5wa\xa1s\x7f\x1c\xd4W]e\xe74\x9bE\xef\xef\xca\xf8\xbc\xe0\xe7eSt&+\x90\xcb\t\x94\xc5\xf9\xd7Rv~\xdb\xee\xdd\xbd=\xe2\xe9i\x98\x9b\x83\xcb/\x87\xcd\x9baa\xc1\x8eU\xc51\x9c\x9e\xb66\x1dw\x1cl\xdf\x0eG\x1ca\xe1\xebT\x17E\x94\xec\xf7{\xf6\x94\xd5\x02\xcfp^\x03\xfc\x0e \xca\xb4\x022\xd3\xdf\x90\xcd\xfd\x0b*+M\xcb}\x80\xf3\xce3\x8d\xf09\xbf\x1b\xcd\xceVo:\xf0>\xac[\x97\xce\xf9\x9d\xcc\xbe\x93[\x85\xe7\x9f7\xabQ\xdc\x07p\xf6]D/\xe6\xb1\x00Y\x01\xe0\xdb\xb9\x9f\x88LNy\x03x\xd0A\xd2m\xb7\xf5\x1f\xbc\xd8|n\xde\x9c\x9a\xdeQ\x81\xc0\xcd\xfe\x87>\x94z\xfb\xdd\xcc\xbedS\\\xab%\xcd\xccH\xe7\x9cc\xe7\x96\x07\x00\xc9\x14sQ\xb01\xc8\xab\xf8\x13C\xa5\x1b;?\xa7\xfd\xb70\x17\xe7$I\x05\xb8e\xcbR!\xf7\x03\xc1m\xb7\xd9y\xa3\x08\x11]\xf8\xeb\xd6I\xaf\xbe\x9aM\xf8\x0e\xf0\xd3OO\xc1_n\xbb\\1_\x10\xbcOeX\x02Y:sCV\x98\xc1QVn\xc3\x93$\x1d\x0c\x07\x81\x9b\xfbn\xe4\xdf{\x88\xb8\x9c\x96\xa0S\xa8\x97E\xf8{\xf7J\xa7\x9e\x9a\x82v\xb8\xed\\\x1f\xe47\xf8#cG\x90\xe0\xfd\xb2\\\xf7\xe158I\xd2\x81\xdd\xb4i\xa9\xa6w\xa3Q\x84\x88\xb1\xd9\xf7P/\x8b\xd9\xdf\xb3\xc7\xd6;\xe2k\x0c\x87=\xbf\xe0\xce\xd8\x82\x0f\n\x007\xff\xae\xfd\xc3\xdd\xd6\x1d\x83 \xabO\xe0\xdf\xfbt0LK\xe0m[\xb3&5\xfb\xbd\xda\xe7\xc2\xdf\xb7/\x15\xfe\xf05\xdf3\x91\xdf\x12\x9c(S\xe0\xc1\xac\x80\xcc\xfb_)\xd8\xaea\xcc\xff\xdd@\xd0>\x1d\xf4\xb3\x04>\x1d\x0cs\xd986\xfb/\xbd\x94M\xf3%\x8bl\x96\xcf\xec;\xbb\x9c.\n\x00\xc8\x1f\x12*]\xf8\xf9x\xb8\xe0\xf2e\xf4\x94\xe1\x13\x949\x1dx[\xd6\xaf\xcf7\xe7\xcf\xcc\xa4\x0e\xdf\xf2\t_\xb2)\xa0%\xf8\xcf \xc3\xfc\x8e\xa0\x82\xd9\x10|1\\ty\xb3z:\xf9\x04yC\xc42@\xe0\xc2_\xbdZz\xf9\xe5l\xc2\xf7P\xef\xcc3\xed\xdc\xe1\xce\xf9\x9d\xd8\xb3\x8b^\x16\xacV\x94\x99\x9d\x07\x00\x1e\xfb\xbf\x18\xa1jy;\x12[\x82\xcd\x9b\x97\n\xb9\x1b\x95\xb9l\x1c\x87z\xfd\x96w]\xf8\xde\xc6\xd1h~\xcc\x1e\xad]\x13\xe4\x98oM \xa0fJ\xf0\xf4\xc8\x00\xd0\x0e\x82\xe5\x9c\x0e\xfc\x9e\xd5\x0e\xf5\xfa\x01\xa0%\xb8:7\x00\x94&v^\xaa2\x97~\x8b\x80\xc0\x07\xd3\xa7\x83~ pK1\x08\x08bo\xbf\x9a\xa1^\x16\xf6\xa5\xe1\x9f*\x14\xc4V\xd6i \x02\xc0\x95\x11\x9aF\xdb\xa1\xe5\n\x11;\x85zY\x84\xbfw\xefr\x86zy\x00\xb0Oi\x86qv\x00\xc8\xa6\x80?\xae\x0c\x00\x1c\x04n\x9a\xb7n]\xaa\xe9\xfd,A\x16\x9f \xde\xc9\x93\'\xd4\x9b\x9d\x95N;\xadJ\xc2\x8f\x010#8:3\x00\x94:\x7f\xab\x94\xae\xfeU\xa7\x9aGl\t\xca\xf4\tb\xe1\xe7\r\xf5\xaa\'|g\x0f\xdd\xb7\xc6\x96=+\x00\x0e\t\xe8\xa9\x16\x00\x1c\x04>\xd8>\x1dd\xb5\x04\x9d@\x10\x87zY5\xbf=\xd4\xab\x9e\xf0c\x00l\xce\x03\x00\x8f\xff\xd7\xc9R\x91\xcb\xac\xba].\x08\\k\xf3\x86\x88\xb1O\xe0\x82[\xbbVz\xfd\xf5l\xc2\x97\xcc\xaa\x8c>\xd4\xeb\xc7\xbev\xf3\r\xd9\x8an\xff\xe7\x02J\x1d\xc0\xdb\xdbPT=\xee\xe4\x13d\x9d\x0e|\xb1\x08\xa4\x0f\x7f8\x9f\xd9\xdf\xb7\xaf*\xa1^\x16\xf6\xf0\xfdWc\x05\xcf\x02\x80\xad\x95\x07\x80\x83\xc0\x85\xe0\x96 +\x08n\xbaI:\xfe\xf8|+|\xd5\n\xf5\xb2\x02\xa0%\xf8\x95\xbc\x00\xd8V\x0b\x008\x08\xf2.\x1b\xbb6\xef\xde\x9d]\xf8\xd5\x0b\xf5\xb2\x02@\xdd\x000\x1e\x05\x1c\xa4t\x13\xe6\xc6\x8d\xb0m\x9bm\xd4\x9c\x9f\xef~N\xa3a\xe7\x1d~\xb8}v\xdb\xc0\xd9j\xd9o\x17\x16\xe0\x82\x0bl\xd3g\xb3\xd9\xfb\xda5\xa2\xf1\x00\x00\x98\x10[-\x13\xe4\xa5\x97\xc2\xd6\xad&\xa8\xb9\xb9\xee\xe7x\xdea\xb7\xdd\xc5.\xfc\xbd{\xe1\xac\xb3\xe0\xa1\x87\xc6J\xf80N\x00\x80\x14\x04\xcd&\\v\x99m!_\xb1\xc2\xb4\xb7\x1b\xf5\x12~\x92\xc0\xcc\x0cl\xd8\x00\x8f<\xd2\xdf\xaa\xd4\x90z\x85\x05\xf5\xcc\xcb\x96\xd2\xbc\x81\x8d\x1bM\x88\x97]\xd6[\xd3;]\xa3\xd10\xeb\xb1a\x03<\xf8\xe08h~\xc7\xc6w\xb2\x00\x92%\x80\xac\n\xffW$\xfb"\x07\xc5>\xc1\xe5\x97\xc3-\xb7\x98\xf0\xb2\xd4\x1ap\xd7\xe9\xd5W-;y<\x84\x0fpD\xa7\x83K\x00 \x13v\x0bK\xfd>\xc1\x0e\xd5\x10\x00\xb0T\xe3o\xbc\x11v\xedJ\x8f\xf7"\x9f\xf7\xb7oO\xe7\xfc^SH\xf5\xc9;|j\xf8\xec-\xcf(\x0c\xbc\xa56a`\'\xee\xf4T\xaf[\xeea;yH\xe8\xbb\x8d\xab\x98\x8b\x98?\x0c\\\x17\xe4\xda?\x0c\x0c\x96\xe0\xe0"\xb0\x1b)y\xae\xde\xfa\xf5\xe6\xbc\x1dy\xa4\x99\xffFF\x9fwj\xca\xce\xbf\xe4\x12\xd8\xb4\xa9z\xb9\x88\x83\xd1\xcfu:\xd8qDB\xc1\xc7z\xbe\xe00N\xd4\xfc\xeew\xe1\xa8\xa3z\'j\xf6\xba\x8e\'\xa4n\xd9b>\x80\xd7\xfb\xa9\'u\x94\xe7x\x85\x81.\xfc\xd5\xabM\xf8\x1f\xf8\x80\xfd\xdf+K\xb7\x97c\xb8b\x85\t\xde\xd7\x15\xdc\x8a\xd4\x17\x04\xfb\xd1\xf8\x00\xc0\x85\xbfv-\xec\xdc\t\xc7\x1ek\x02\x9b\xee\x12\xe9\xba\x93\xe8\xb5|\xba\x91;\x81>\x1d\xb85\x19\x13\x10\xf4\x02@}\xa6\x80\xbc\xf9\xf9\xbe\xc8\xf3\xc6\x1bp\xef\xbd\xa6\xd5\xbd\xc2\xbc\xaa\xd7\'\xe8O"\x8d\x06\xfa\xfe\xd2\xa3\x80\xbbj\x11\x05\xe4\xcd\xcf\xf7H`\xcf\x9et\'\xcf\xb6mv,\xebS\xc4*\xd5\'\xc8\x1e\x05\x9c\x18\xe4\xda\xf7i\xa0\xe7\x03^\xa3\xea\xbe\xa8\xd9\xb8H~\xbe\xef\xe4Y\xb1\xc2>\xebX\x9f\xa0?\xc7\t"k\x94%AD\xe9\x96\xb0\xa6,\xc1\xd0/4\xea\xcet\x16~\x91\xfc|\xcf!\xcc\x9b\x8bX\x85\xfa\x04\xd9\xd8\xad\xf7M\xb1u\xcf\n\x80\xf7\xb4!i\xd4\x9d\xd9_\xf8e%m\xd4\xad>A~\x00\xdc+\xd3\xfel\x00\x90\xd5\x058D\xb0#\\\xa0:\xafu\x1dV~~]\xea\x13\xe4\xe3\x85\x00\x82\xcb\xe2\xe9=\x0b\x08\xdc\x11\xfc\xbcL\xfb\xab\x91\x170\xec\xfc\xfc\xaa\xd7\'\xc8\xc7n\xb5\xdfR\x9a\xe9\x9d;3\xe8\xcb\xe1"\xa3\x07\xc0r\xe5\xe7W\xb5>\xc1\xe0\x00\x90\xec\xe1^.\x008bN\x11\xfc\x9f\xcc\x94\x8c\xce\x0fX\xee\xfc\xfc\xaa\xd5\'\x18\x8c=z{@p\x90\xf2\x16\x8cR\xea\x0c>\x1b.4\x1a?`T\xf9\xf9U\xa9O08\xcf\x86\xcfK\x82\x1c\xf3\xbd\xccC\xa93\xf8\x88L\xfb\x97\x1f\x00\xa3\xce\xcf\x1fu}\x82b</K\x0c\xfd|\x90g\xbebQJ\xa7\x81s\xa3\x0b._\x07\xaa\x92\x9f_\xcf\xe9\xc0\x95\xf5\xc5\xd8\x9a\xe7\x05\x80\x97\x88\xfb\x88\xe0\x7f\x95&\x18\x0c\xbf\x03U\xcb\xcf_\xee\xfa\x04\xc5\xd9}\xb6;\\\x96\xb9\x01\x10N\xf4e\xe1\x07\x94\xbe\xdb~\xf9\x84_\xa5\xfc\xfcz\x85\x88n\xadO\x8d\xad\xf9 \x00\x98\x92Y\x81\xcf\x84\x0b\x0e\xd7\x02T=?\x7f\xd8\xf5\t\xcaa\xd7\xfeg\x05G\xab\xc0\x1b\xc5bGp\x85\xe0\xd1p\x83\xe18\x83u\xc9\xcf\x1fV}\x82\xf2x1p9/\x8fP\x08\x1f\x047\x04d\xcd\x96\xde\xe8\xba\xe5\xe7\x97]\x9f`8\xfc\x8b*R%4\xb6\x02\xe1\xf3\x97\x82\xf0\xcb\xb5\x00^.}\xdd\xbaz\xe5\xe7\x97Q\x9f\xa0\xfc\x15\xc3y\x99\x92\xde\'{\xb5O9\xef\x0fR\x1a\x12\x96[3\xa0\xd10>\xf2\xc8z\xe6\xe7\x17\xa9Op\xf3\xcdv^\xb9%\xe3}\xff\xc6\xc9A^\xe5l\xf9\x939\x12S\x82_\x16\xbc\x19!\xadX\x83\xbd\xf3\xd7]\xd7_\x83\xaa\x9a\x9f\x9f\xb7>A\xabe\x96\xe0\xcd7\xa5\x13N(\xeb\xd5q.|\t\xfe\xa9T\xe1\xc7 \x08\x9fw\xb5\xddpp\xf6\x8e?\xf7\\\xf7\xb7\x86\xc5\xc2\xafj~~\xdeec\x07\xfa\xd5W\x97\xd5\x17/\xe4\xbdW\xf0\xeb\n\n\x9bE\xaey_\x1a\xd5\x00n\x00\xf6\xe5\x87P\x0f\xea\xf5f\xd0:\xe4\xe7K\xf9\xeb\x13\x94K-l\xcd\xe6\xc1\x04\x1e\x03H\x86\x91\xdc\xab\xf4\xed!_W\xba\xd9`p\xe4\xfa\x14\xf0\xb5\xafu6\x9d\xee\x0f\xcc\xccTc\xce\xcfb\t:-\x1b\xc7\x96\xcd_\x1e\xf9\xf6\xdb\xd2\xc9\'/=gp\xf6\x97D\x9c\xa4A\xcb\xc3g\x04\x80W\x10[\xd3f~\x06kx\xa3a\x03\xf0\xc1\x0fJ?\xfbYj\x1e\x9d%\x9b\xf3GWu{0\x10\xb4\x87\x88q\xbf\x9c\xee\xb9g\xa9\x12\x14\x13\xbe\x04\xff(S\xd0\xe2/\x8a\xea\x03\x02_\x1d\xbc^\xb64\\\xcc\n\xb8\x1fp\xd2I\xd2SO-\xb5\x00O?-}\xe2\x13\xf6}\x955\xbf\x13\x08\x1c\xac\xb7\xde*\xed\xda\x95\xf6i\xcf\x1e\xe9\xee\xbb\xed}\xc9\xc5W\x05\xfd\xed \xaf(k\x11\xa86\x1a\xf4\xf5\xf1^\\\xe5\x19\xe08l\x0e\x1a\xdc\xeb\x8c_\x11\x7f\xf1\xc5p\xe8\xa10;\x0b\xb7\xdfn\xc7\xa6\xa6\xb2\xe5\xf6W\x89\x92\xc4|\x97\xc5EKR=\xfbl;\xfe\xbd\xef\xc1\xe3\x8f/\xed\xf3\xe04\x87-\xd4mL`\xb3\xa0\x99t)\x04\xd1\xb5\x99\x83\xdc5\xa0\xac\x01|\x0cx\x00x\x0f\xe9\xb1\xc1\xc83w\xe34-w\x0e{\xa5nU\x9d\x1a\x8d\xfd\xdb\xdf\xe9X~Z\xc4\xe6\xfa{\xb1g\xfe\xad\x04r\x172\x18H`\xe1]\xf5$\xf08p\x0f\xe6\x81\x16\xebQ\xabe<=m^\xfe\xf4t0r5\x16>\xa4QL\xb3i\\\x8e\xf0\x85\x01\xe0\x1d\xe0\x86\xc4,\xc1@\xe6\xa4\xd02\xa1\xcc\xfc,\x02\xdf\x06\xce\xc2\xcc\xcfp\x9d\x90\t\x81i\xfa4\xf0\xa9\x04\xfeA05h\xd8Wt\xb5h1\xdc\xf8\xcfHMR\xcdU\xb6\xf24\x8f\t\x7f\x07\xb6O\xa3\x90\xf5-\x04\x80\xc4b\xcf\xa9\x04\x1e\x04.\xc4\x90\xd9`@s4\xa1\xbe\xb4\x88Y\xd8\xc7\x80\xb3\x81YL\t\x07\x1e\xef\xc2\xeb\xc5\x01\x04\xcd\x04\xee\x07.\x02\xde\xc2\x800\x01A\xb9\xe4Z\xbe\x1d8\x17\x13~RD\xf8P\xd2\x03\x83\xc4\xd6\x02\x0eJ\xecA\xc470\x94Vh\xad\xb6\xf6\xe4N\xdf\x14pe\x023\x98\xe5-<\xdd\x96\xf9\xc4h6\xacB\xfd\x11\xb0\x13s\x10k]_\xad"$L\xd0M\xe0\n\xe0\x19\xc1\xf4 !\xdf\xd0I\xe9\xe6\x91\x95\xb2|\x02\xa9\nie\xf5\xe5\xf8u\xbdW\x84\xb1\xadvY\x1f\xa5\xdb\xc9\x0f\x13<\x14\x1a_\xed*#\xd5\xe48)\xf7\xca0\xb6\x83\xbf\t|9I\xe9C\xa3\xc3\x94n&\xf5\x17\x19\x8ez`\xeb\xc0\xf1\x93\xd6/\x84\xb1\xcc\x97\xda5jR\xba\x81\xe4`\xa5u\x06\xaa\xf9\xfe\xa1jq\xbc\xd1fc\x18\xc3z.\xaei\xa9%\xf8]\x99\xa38\x9a<\xc3z\xb0k\xfd\xc3\xcaZ\xd4\xa9\xea\xa4h\xb9Y\xf0\xc9.H\x9fp*\xfc\x87\x94\xbe\xe9\xb3\x1es~?RT\x9fFp\xbe,kU\x9a\xf8\x05\xd2\xd2\xda\x0b\x8f\t\x0e\r\xe34\x1e\xc2\x8fI\xe9\x94p\xac\xe0\xce\x0e\xe8?\x908\xf6\xf2g\x05\x17\t\x0e\x8a\xc7i,IQ\xbd\x1a\xc1\x85\xb2\n$\x0e\x82\x03\xc57\x88\x01\x7f\x97\xc2|\xef\xe32:\xe9,\x13\xc9\xd6\n\x1c\x08\x1f\x15\xdc\x1a\r\xc8\xc2\x98\x02\xc1\xb7o\xb9\xf0_\x17\\\x15\x8d\xc9\xe0I\x9cu%E\xf3\x9c\xe0K\x82\xa7\xa2\x01\x1b\'\xff\xa0\xbd\xc6\xd2\xdf*\xdd\xc3\x97y\x0f\xffX\x92\xcc\x1ax\x1d\x82U\x82\xdf\x17<\xd96xu\xb5\x08\xed\x91\xce\xb7\x05\'E}\xafg|?\x0cj\xb3\x06+\x04\xbf\'x)\x1a<7\xa1U\xb7\n\x9e\x9e\xed\xed\x9c\x17|K\xf6\xfc\xde\xfb7\xa5qv\xf4\x06%\xb5%5\xc8\xf6\xb9\xff\x81\xe0\xf9\xb6A\x9e\x8f\x06z\xd4\x02\x8f\x85\xde\x1e\xcd\xfc\x8d\xd2\x975M\x04\x9f\x95\x02\x10b\x8b\xb0J\xb0Vpw\x07\xb3:\xa7\xd4_X\x8e\xa5f\xbf\x87\x97\xccio\xcf\x13\x82+\x04k\xda\xfas\xe0\xce\xf3EHm\x0b"\x82_\x93\x85\x8fO\x08~\xdcEH\xf3\x11\x97!p\xbfV7\x8b\xf3\xdf\x82;\x04g\x0b\x0e\x8f\xdaZ\xbc@\xc3\x90\xa9\x16a\x87\xac\x9d\t\xd0\x887B\x08\x8e\xc6\xb6\xa15\x80?\xc1\xdet\xd6 ,\xa8\x04\xea\xb7kF\xf4\x1e\x87v\x01\xee\xc1\xb4\xf9a\xe0\x9f\x81\xb7\x93P\x8d+\xba\xe0\xbb\x9bc\x8bn\xd9\x1a6\xd5\x02\x001E\xa6\xb4\x15\x0f\xae\xec\xb5h\rl\x1d\xfdZ\xaco\xbf\x00|\xba\xe0-w\x01\x7f\x87Y\xa2\x1f`\x89\x18S\t\xbc\x11\xdd\xdb\x01\x9a\xb4\xb7\xab\xeaT;\x00\xc4\x14\x06~\x1aP\xb7-R\n\xf1v\x1b%\xf6\x15\xef\xc5\x9c\xb4ob\xe0\x89\xad\x85[\x867\x12x\xa9\xcb\xb5\x9b\xbd\xee]\x07\xaa5\x00b\xd2\xd2\xbe\xb8\xdf\xb0X\xc6\xc6I\xa5\xf1z\x8b\x9a\x98\xf6\xac46\x00\xe8F}\x9c\xb0$\xfd\xd9\xbbV\xa1\xd3\x8f&\xc9.\x13\x9a\xd0\x84&4\xa1q\xa3\xff\x07\xa7\x89Cv\xddM\xb8\xcc\x00\x00\x00\x00IEND\xaeB`\x82'


class RunManager:
    __slots__ = "funcs", "started_exec"

    def __init__(self) -> None:
        tk.Tk.report_callback_exception = lambda *a: self.report_exc(False)
        self.funcs:list[tuple[Callable,bool]] = []
        self.started_exec:bool = False

    def __new__(Class:type, *args:tuple, **kwargs:dict) -> RunManager:
        singleton:Class|None = getattr(Class, "singleton", None)
        if singleton is None:
            Class.singleton:Class = super().__new__(Class, *args, **kwargs)
            _init = getattr(Class, "_init", None)
            if _init is not None:
                _init(Class.singleton, *args, **kwargs)
        return Class.singleton
    _init, __init__ = __init__, lambda self: None

    def register(self, func:Callable, *, exit_on_error:bool=False) -> None:
        assert not self.started_exec, "Can't register any functions after " \
                                      "calling .exec()"
        self.funcs.append((func, exit_on_error))

    def exec(self) -> None:
        def _format_args(args:object) -> tuple[object]:
            return tuple(args) if isinstance(args, tuple|list) else (args,)

        assert not self.started_exec, "You already called .exec()"
        self.started_exec:bool = True
        args:object = ()
        for func, exit_on_error in self.funcs:
            try:
                args:object = func(*_format_args(args))
            except BaseException as error:
                if not isinstance(error, SystemExit):
                    self.report_exc(critical=exit_on_error)
                    if not exit_on_error:
                        continue
                return None

    def report_exc(self, critical:bool, msg:str="") -> None:
        if critical:
            pre_string:str = " Critical error ".center(80, "=")
        else:
            pre_string:str = " Non critical error ".center(80, "=")
        string:str = pre_string + "\n" + format_exc().rstrip("\n") + "\n"
        if msg:
            string += msg + "\n"
        self._display(string + "="*80)

    def _display(self, string:str) -> None:
        try_n:int = 0
        while True:
            try:
                if try_n == 0:
                    _display0(string)
                elif try_n == 1:
                    _display1(string)
                elif try_n == 2:
                    _display2(string)
                else:
                    pass # No display, ignore the error
                break
            except Exception as error:
                print(error)
                try_n += 1


# Different displays
def _display0(string:str) -> None:
    from bettertk import BetterTk, make_scrolled

    root:BetterTk = BetterTk(className="Error")
    frame, text = _setup_window(root, string)
    make_scrolled(frame, text, vscroll=True, hscroll=True,
                  lines_numbers=True)
    root.mainloop()

def _display1(string:str) -> None:
    root:tk.Tk = tk.Tk(className="Error")
    frame, text = _setup_window(root, string)
    text.pack(fill="both", expand=True)
    root.mainloop()

def _setup_window(root, string:str) -> tuple[tk.Frame,tk.Text]:
    def close() -> None:
        root.destroy()

    root.title("Error")
    root.protocol("WM_DELETE_WINDOW", close)
    if _try_set_iconphoto(root):
        string += "\nAlso `root.iconphoto` on error window failed :/"

    frame:tk.Frame = tk.Frame(root, bg="black")
    frame.pack(fill="both", expand=True)
    button:tk.Button = tk.Button(root, text="Write error to file",
                                 command=lambda: _display2(string),
                                 **BUTTON_KWARGS)
    button.pack(fill="x", expand=True)

    text:tk.Text = tk.Text(frame, bg="black", fg="white", width=80,
                           height=20, bd=0, highlightthickness=0,
                           insertbackground="white", wrap="none")
    text.insert("end", string)
    return frame, text

def _display2(string:str) -> None:
    with open(err_path, "w") as file:
        file.write(string)


def _try_set_iconphoto(root:tk.Tk|BetterTk) -> HasErrorer:
    try:
        from bettertk.terminaltk.sprites.creator import SpritesCache
        sprite:Image.Image = SpritesCache(256, 256>>1, 220)["error"] # warning
        root.iconphoto(False, sprite)
        return False
    except:
        pass
    try:
        from PIL import Image, ImageTk
        from io import BytesIO
        img:Image.Image = Image.open(BytesIO(ERROR_IMG_DATA))
        try:
            root.iconphoto(False, img)
        except:
            root.tk_img_895644 = ImageTk.PhotoImage(img, master=root)
            root.iconphoto(False, root.tk_img_895644)
        return False
    except:
        pass
    return True


if __name__ == "__main__":
    def start() -> int:
        global root
        root = tk.Tk()
        root.after(200, lambda: 1/0)
        root.bind("<Delete>", lambda e: 1/0)
        return 1

    def init(arg:int) -> tuple[str,bool]:
        assert arg == 1
        return ("123", False)

    def run(arg1:str, arg2:bool) -> None:
        try:
            root.mainloop()
        except KeyboardInterrupt:
            return None

    manager:RunManager = RunManager()
    manager.register(start, exit_on_error=True)
    manager.register(init, exit_on_error=False)
    manager.register(run, exit_on_error=False)
    manager.exec()