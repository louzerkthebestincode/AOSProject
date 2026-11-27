from __future__ import annotations

import logging

from ..concurrency.runner import SimulationRunner, WorkerSpec
from ..core.resource_manager import ResourceManager

logger = logging.getLogger("deadlock_simulator")


def run_safe(timeout: float = 8.0, check_interval: float = 0.25) -> tuple[int, dict[str, int]]:
    logger.info("=== SCENARIO: SAFE (NO DEADLOCK) ===")
    rm = ResourceManager({"R1": 1, "R2": 1, "R3": 1})
    specs = [
        WorkerSpec("P1", ["R1", "R2"], hold_delay=0.5, timeout=timeout),
        WorkerSpec("P2", ["R2", "R3"], hold_delay=0.5, timeout=timeout),
    ]
    runner = SimulationRunner(rm, use_detector=True, check_interval=check_interval)
    code = runner.run(specs)
    return code, runner.results


def run_deadlock(timeout: float = 8.0, check_interval: float = 0.25) -> tuple[int, dict[str, int]]:
    logger.info("=== SCENARIO: DEADLOCK (2 PROCESSES + DFS RECOVERY) ===")
    rm = ResourceManager({"R1": 1, "R2": 1})
    specs = [
        WorkerSpec("P1", ["R1", "R2"], hold_delay=0.8, timeout=timeout),
        WorkerSpec("P2", ["R2", "R1"], hold_delay=0.8, timeout=timeout),
    ]
    runner = SimulationRunner(rm, use_detector=True, check_interval=check_interval)
    code = runner.run(specs)
    return code, runner.results


def run_philosophers(
    n: int = 5,
    timeout: float = 10.0,
    check_interval: float = 0.25,
) -> tuple[int, dict[str, int]]:
    logger.info(f"=== SCENARIO: DINING PHILOSOPHERS ({n} THREADS, DEADLOCK + RECOVERY) ===")
    forks = {f"Fork_{i}": 1 for i in range(1, n + 1)}
    fork_names = list(forks.keys())
    rm = ResourceManager(forks)
    specs = [
        WorkerSpec(
            f"Philosopher_{i + 1}",
            [fork_names[i], fork_names[(i + 1) % n]],
            hold_delay=0.8,
            timeout=timeout,
        )
        for i in range(n)
    ]
    runner = SimulationRunner(rm, use_detector=True, check_interval=check_interval)
    code = runner.run(specs)
    return code, runner.results


def run_prevention(
    n: int = 5,
    timeout: float = 10.0,
    check_interval: float = 0.25,
) -> tuple[int, dict[str, int]]:
    logger.info(f"=== SCENARIO: TOTAL ORDER PREVENTION ({n} PHILOSOPHERS, 0 DEADLOCKS) ===")
    forks = {f"Fork_{i}": 1 for i in range(1, n + 1)}
    fork_names = list(forks.keys())
    rm = ResourceManager(forks, enforce_total_order=True)
    specs = [
        WorkerSpec(
            f"Philosopher_{i + 1}",
            [fork_names[i], fork_names[(i + 1) % n]],
            hold_delay=0.4,
            timeout=timeout,
        )
        for i in range(n)
    ]
    runner = SimulationRunner(rm, use_detector=True, check_interval=check_interval, use_total_order=True)
    code = runner.run(specs)
    logger.info(f"Task: PreventionSummary | Deadlocks detected: {rm.deadlocks_detected} | Code: {code}")
    return code, runner.results


def run_errors(timeout: float = 1.0, check_interval: float = 0.25) -> tuple[int, dict[str, int]]:
    logger.info("=== SCENARIO: CONTROLLED ERRORS (MISSING RESOURCE + TIMEOUT) ===")
    rm = ResourceManager({"R1": 1})
    specs = [
        WorkerSpec("P_MissingRes", ["R99"], hold_delay=0.2, timeout=timeout),
        WorkerSpec("P_SlowHolder", ["R1"], hold_delay=2.5, work_delay=0.2, timeout=5.0),
        WorkerSpec("P_Timeout", ["R1"], hold_delay=0.2, timeout=timeout),
    ]
    runner = SimulationRunner(rm, use_detector=False, check_interval=check_interval)
    code = runner.run(specs)
    return code, runner.results


SCENARIOS = {
    "safe": run_safe,
    "deadlock": run_deadlock,
    "philosophers": run_philosophers,
    "prevention": run_prevention,
    "errors": run_errors,
}