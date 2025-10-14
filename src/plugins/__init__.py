from .virtualevents import VirtualEvents

from .python import PythonPlugin
from .cpp import CppPlugin
from .c import CPlugin
from .sh import ShPlugin
from .java import JavaPlugin
from .basic import BasicPlugin


# Order which to check the plugins
plugins:list[type] = [
                       PythonPlugin,
                       CppPlugin,
                       CPlugin,
                       ShPlugin,
                       JavaPlugin,
                       BasicPlugin,
                     ]