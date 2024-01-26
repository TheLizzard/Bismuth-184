from .virtualevents import VirtualEvents

from .python import PythonPlugin
from .cpp import CppPlugin
from .c import CPlugin
from .java import JavaPlugin
from .all import BasicPlugin

plugins = [PythonPlugin, CppPlugin, CPlugin, JavaPlugin, BasicPlugin]