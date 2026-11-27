from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time


class ProcessState(str, Enum):
    """Linux kernel process state codes used by the simulator."""
    RUNNING = "R"          # Running or ready
    SLEEPING = "S"         # Interruptible sleep (waiting for a resource)
    UNINTERRUPTIBLE = "D"  # Uninterruptible kernel sleep
    STOPPED = "T"          # Stopped or traced
    ZOMBIE = "Z"           # Terminated, awaiting reaping
    IDLE = "I"             # Idle kernel thread


@dataclass
class Process:
    pid: str
    state: ProcessState = ProcessState.RUNNING
    exit_code: int | None = None


@dataclass
class Resource:
    res_id: str
    capacity: int = 1

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"Resource '{self.res_id}' capacity must be >= 1, got {self.capacity}.")


@dataclass(frozen=True)
class SimulationEvent:
    action: str
    pid: str
    res_id: str | None = None
    detail: str = ""
    timestamp: float = field(default_factory=time.time)


class ResourceNotFoundError(LookupError):
    """Raised when a process requests a resource that does not exist."""


class DeadlockVictimError(RuntimeError):
    """Raised when the recovery policy aborts a process in a deadlock cycle."""


class OrderViolationError(ValueError):
    """Raised when a request violates the total ordering prevention policy."""