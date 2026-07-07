from __future__ import annotations
import subprocess
from pathlib import Path
from .actions import Observation

class FeedbackSensor:
    """Runs deterministic validators and returns observations to the loop."""
    def __init__(self, workspace: Path, commands: list[str]):
        self.workspace = workspace.resolve()
        self.commands = commands
    def collect(self) -> list[Observation]:
        observations: list[Observation] = []
        for command in self.commands:
            try:
                proc = subprocess.run(command, cwd=self.workspace, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                msg = proc.stdout + proc.stderr
                observations.append(Observation("feedback", proc.returncode == 0, msg or f"{command} exited {proc.returncode}", {"command": command, "returncode": proc.returncode}))
            except Exception as exc:
                observations.append(Observation("feedback", False, f"{type(exc).__name__}: {exc}", {"command": command}))
        return observations
