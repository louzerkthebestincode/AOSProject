from .catalog import (
    SCENARIOS,
    run_deadlock,
    run_errors,
    run_philosophers,
    run_prevention,
    run_safe,
)

__all__ = [
    "SCENARIOS",
    "run_safe",
    "run_deadlock",
    "run_philosophers",
    "run_prevention",
    "run_errors",
]