from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time

from ..core.resource_manager import ResourceManager
from ..domain.models import (
    DeadlockVictimError,
    OrderViolationError,
    ResourceNotFoundError,
)

logger = logging.getLogger("deadlock_simulator")


@dataclass(frozen=True)
class WorkerSpec:
    pid: str
    resources: list[str]
    hold_delay: float = 0.8
    work_delay: float = 0.4
    timeout: float = 8.0


class SimulationRunner:
    def __init__(
        self,
        resource_manager: ResourceManager,
        use_detector: bool = True,
        check_interval: float = 0.25,
        use_total_order: bool = False,
    ) -> None:
        self.rm = resource_manager
        self.use_detector = use_detector
        self.check_interval = check_interval
        self.use_total_order = use_total_order
        self.results: dict[str, int] = {}

    def _worker(self, spec: WorkerSpec) -> None:
        self.rm.register_process(spec.pid)
        logger.info(f"Task: Lifecycle | Start | {spec.pid}")
        acquired: list[str] = []
        exit_code = 0

        requested = (
            self.rm.order_policy.order_requests(spec.resources)
            if self.use_total_order
            else list(spec.resources)
        )
        if self.use_total_order:
            logger.info(f"Task: Prevention | {spec.pid} sorted order: {requested}")

        try:
            for res_id in requested:
                self.rm.request(spec.pid, res_id, timeout=spec.timeout)
                acquired.append(res_id)
                if self.rm.shutdown_event.wait(timeout=spec.hold_delay):
                    raise InterruptedError(f"{spec.pid} interrupted during hold.")

            logger.info(f"Task: Work | {spec.pid} executing critical section")
            self.rm.shutdown_event.wait(timeout=spec.work_delay)

        except DeadlockVictimError as exc:
            logger.error(f"Task: Recovery | {spec.pid} aborted: {exc} | Code: 4")
            exit_code = 4
        except (ResourceNotFoundError, OrderViolationError, ValueError) as exc:
            logger.error(f"Task: InputError | {spec.pid}: {exc} | Code: 2")
            exit_code = 2
        except TimeoutError as exc:
            logger.error(f"Task: Timeout | {spec.pid}: {exc} | Code: 3")
            exit_code = 3
        except InterruptedError as exc:
            logger.warning(f"Task: Shutdown | {spec.pid}: {exc} | Code: 130")
            exit_code = 130
        except Exception as exc:
            logger.exception(f"Task: UnexpectedError | {spec.pid}: {exc} | Code: 1")
            exit_code = 1
        finally:
            for res_id in reversed(acquired):
                try:
                    self.rm.release(spec.pid, res_id)
                except ValueError as exc:
                    logger.error(f"Task: CleanupError | {spec.pid} releasing {res_id}: {exc} | Code: 1")
            clean = self.rm.mark_terminated(spec.pid, exit_code)
            self.results[spec.pid] = exit_code if clean else 1
            logger.info(
                f"Task: Lifecycle | End | {spec.pid} state=Z released_ok={clean} | Code: {self.results[spec.pid]}"
            )

    def _detector_loop(self, stop_event: threading.Event) -> None:
        logger.info("Task: DetectorDaemon | Start | Background DFS monitoring active")
        while not stop_event.wait(timeout=self.check_interval):
            self.rm.detect_and_recover()
        logger.info("Task: DetectorDaemon | End | Stopped cleanly | Code: 0")

    def run(self, specs: list[WorkerSpec]) -> int:
        stop_daemon = threading.Event()
        daemon: threading.Thread | None = None
        started: list[threading.Thread] = []

        if self.use_detector:
            daemon = threading.Thread(
                target=self._detector_loop,
                args=(stop_daemon,),
                name="DFSDetectorDaemon",
                daemon=True,
            )
            try:
                daemon.start()
            except RuntimeError as exc:
                logger.critical(f"Task: ThreadStart | Failed to start detector daemon: {exc} | Code: 1")
                return 1

        try:
            for spec in specs:
                t = threading.Thread(target=self._worker, args=(spec,), name=spec.pid)
                try:
                    t.start()
                    started.append(t)
                except RuntimeError as exc:
                    logger.critical(f"Task: ThreadStart | Failed to start {spec.pid}: {exc} | Code: 1")
                    self.rm.trigger_shutdown()
                    return 1

            while any(t.is_alive() for t in started):
                for t in started:
                    t.join(timeout=0.2)
            return 0

        except KeyboardInterrupt:
            logger.warning("Task: Shutdown | User interruption (Ctrl+C) received | Code: 130")
            self.rm.trigger_shutdown()
            for t in started:
                t.join(timeout=2.0)
            return 130
        finally:
            stop_daemon.set()
            if daemon is not None and daemon.is_alive():
                daemon.join(timeout=2.0)