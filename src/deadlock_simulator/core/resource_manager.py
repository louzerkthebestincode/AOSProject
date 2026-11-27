from __future__ import annotations

from collections import deque
import logging
import threading
import time

from ..domain.models import (
    DeadlockVictimError,
    Process,
    ProcessState,
    Resource,
    ResourceNotFoundError,
    SimulationEvent,
)
from .detector import detect_cycle
from .prevention import TotalOrderPolicy
from .recovery import select_victim, verify_release
from .wait_for_graph import build_wait_for_graph

logger = logging.getLogger("deadlock_simulator")


class ResourceManager:
    def __init__(
        self,
        resources: dict[str, int] | list[Resource],
        enforce_total_order: bool = False,
    ) -> None:
        if isinstance(resources, list):
            cap_map = {r.res_id: r.capacity for r in resources}
        else:
            cap_map = dict(resources)

        if not cap_map or any(cap < 1 for cap in cap_map.values()):
            raise ValueError("Resources must be non-empty with capacity >= 1.")

        self.lock = threading.Lock()
        self.capacity: dict[str, int] = cap_map
        self.available: dict[str, int] = dict(cap_map)
        self.allocations: dict[str, dict[str, int]] = {}
        self.wait_queues: dict[str, deque[str]] = {r: deque() for r in cap_map}
        self.conditions: dict[str, threading.Condition] = {
            r: threading.Condition(self.lock) for r in cap_map
        }

        self.processes: dict[str, Process] = {}
        self.aborted: set[str] = set()
        self.events: list[SimulationEvent] = []
        self.shutdown_event = threading.Event()

        self.enforce_total_order = enforce_total_order
        self.order_policy = TotalOrderPolicy(list(cap_map.keys()))

        self.deadlocks_detected = 0
        self.last_detection_ms = 0.0
        self.last_recovery_ms = 0.0

    def register_process(self, pid: str) -> None:
        with self.lock:
            self.processes[pid] = Process(pid=pid, state=ProcessState.RUNNING)

    def mark_terminated(self, pid: str, exit_code: int) -> bool:
        with self.lock:
            if pid in self.processes:
                self.processes[pid].state = ProcessState.ZOMBIE
                self.processes[pid].exit_code = exit_code
            clean = verify_release(pid, self.allocations)
            if not clean:
                logger.error(f"Task: Verification | {pid} terminated while still holding resources | Code: 1")
            return clean

    def request(self, pid: str, res_id: str, timeout: float = 5.0) -> None:
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}.")

        with self.lock:
            if res_id not in self.capacity:
                raise ResourceNotFoundError(f"Resource '{res_id}' does not exist.")
            if pid in self.aborted:
                raise DeadlockVictimError(f"{pid} was selected as a deadlock victim.")

            if self.enforce_total_order:
                self.order_policy.validate_request(pid, res_id, self.allocations.get(pid, {}))

            logger.info(f"Task: Request | Start | {pid} requests {res_id}")
            self.events.append(SimulationEvent("request", pid, res_id))

            queue = self.wait_queues[res_id]
            queue.append(pid)
            deadline = time.monotonic() + timeout

            try:
                while not (self.available[res_id] > 0 and queue[0] == pid):
                    if pid in self.aborted:
                        raise DeadlockVictimError(f"{pid} aborted by deadlock recovery.")
                    if self.shutdown_event.is_set():
                        raise InterruptedError(f"Shutdown requested while {pid} waited for {res_id}.")

                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError(f"Timeout ({timeout}s) for {pid} waiting on {res_id}.")

                    if pid in self.processes:
                        self.processes[pid].state = ProcessState.SLEEPING
                    logger.warning(f"Task: Wait | {pid} state=S waiting for {res_id} (queue={list(queue)})")
                    self.conditions[res_id].wait(timeout=remaining)

                if pid in self.aborted:
                    raise DeadlockVictimError(f"{pid} aborted by deadlock recovery.")

                queue.popleft()
                self.available[res_id] -= 1
                self.allocations.setdefault(pid, {})
                self.allocations[pid][res_id] = self.allocations[pid].get(res_id, 0) + 1
                if pid in self.processes:
                    self.processes[pid].state = ProcessState.RUNNING

                self.events.append(SimulationEvent("allocate", pid, res_id))
                logger.info(
                    f"Task: Allocation | End | {pid} acquired {res_id} "
                    f"(available={self.available[res_id]}/{self.capacity[res_id]}) | Code: 0"
                )

                if self.available[res_id] > 0 and queue:
                    self.conditions[res_id].notify_all()
            except BaseException:
                if pid in queue:
                    queue.remove(pid)
                self.conditions[res_id].notify_all()
                raise

    def release(self, pid: str, res_id: str) -> None:
        with self.lock:
            held = self.allocations.get(pid, {}).get(res_id, 0)
            if held <= 0:
                raise ValueError(f"{pid} cannot release '{res_id}': not currently held.")

            self.allocations[pid][res_id] -= 1
            if self.allocations[pid][res_id] == 0:
                del self.allocations[pid][res_id]
            if not self.allocations[pid]:
                del self.allocations[pid]

            self.available[res_id] += 1
            self.events.append(SimulationEvent("release", pid, res_id))
            logger.info(
                f"Task: Release | End | {pid} released {res_id} "
                f"(available={self.available[res_id]}/{self.capacity[res_id]}) | Code: 0"
            )
            self.conditions[res_id].notify_all()

    def detect_and_recover(self) -> list[str] | None:
        with self.lock:
            wfg = build_wait_for_graph(self.allocations, self.wait_queues)
            cycle, elapsed_ms = detect_cycle(wfg)
            if cycle is None:
                return None

            t_rec = time.perf_counter()
            self.deadlocks_detected += 1
            self.last_detection_ms = elapsed_ms
            cycle_str = " -> ".join(cycle + [cycle[0]])
            logger.critical(
                f"Task: DFSDetection | DEADLOCK DETECTED in {elapsed_ms:.4f} ms | Cycle: {cycle_str}"
            )

            victim = select_victim(cycle, self.allocations)
            self.aborted.add(victim)
            self.events.append(SimulationEvent("abort", victim, detail=cycle_str))
            logger.critical(
                f"Task: Recovery | Victim selected: {victim} | Policy: Abort & Release | Code: 4"
            )

            for cond in self.conditions.values():
                cond.notify_all()

            self.last_recovery_ms = (time.perf_counter() - t_rec) * 1000.0
            return cycle

    def trigger_shutdown(self) -> None:
        self.shutdown_event.set()
        with self.lock:
            for cond in self.conditions.values():
                cond.notify_all()