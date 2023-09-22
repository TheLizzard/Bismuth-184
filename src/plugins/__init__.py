from .virtualevents import VirtualEvents

from .python import PythonPlugin
from .cpp import CppPlugin
from .all import BasicPlugin

plugins = [PythonPlugin, CppPlugin, BasicPlugin]