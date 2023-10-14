from .virtualevents import VirtualEvents

from .python import PythonPlugin
from .cpp import CppPlugin
from .java import JavaPlugin
from .all import BasicPlugin

plugins = [PythonPlugin, CppPlugin, JavaPlugin, BasicPlugin]