from __future__ import annotations

from ..runmanager import RunManager as BaseRunManager


class RunManager(BaseRunManager):
    __slots__ = ()

    COMPILE:list[str] = ["mvn", "compile"]
    RUN:list[str] = ["mvn", "exec:java", "-Dexec.mainClass=uk.ac.ed.inf.ilp.App"]
    # RUN:list[str] = ["mvn", "test"]