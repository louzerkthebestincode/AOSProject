import threading
import time
import unittest

from src.deadlock_simulator.concurrency.runner import SimulationRunner, WorkerSpec
from src.deadlock_simulator.core.detector import detect_cycle
from src.deadlock_simulator.core.resource_manager import ResourceManager
from src.deadlock_simulator.domain.models import OrderViolationError, ResourceNotFoundError


class TestDeadlockSimulator(unittest.TestCase):
    def test_multi_instance_and_capacity_invariant(self) -> None:
        rm = ResourceManager({"R1": 2})
        rm.request("P1", "R1", timeout=1.0)
        rm.request("P2", "R1", timeout=1.0)
        self.assertEqual(rm.available["R1"], 0)
        with self.assertRaises(TimeoutError):
            rm.request("P3", "R1", timeout=0.1)
        rm.release("P1", "R1")
        rm.release("P2", "R1")
        self.assertEqual(rm.available["R1"], 2)

    def test_fifo_fairness(self) -> None:
        rm = ResourceManager({"R1": 1})
        rm.request("Holder", "R1", timeout=1.0)
        order: list[str] = []

        def waiter(pid: str) -> None:
            rm.request(pid, "R1", timeout=3.0)
            order.append(pid)
            rm.release(pid, "R1")

        t1 = threading.Thread(target=waiter, args=("First",))
        t2 = threading.Thread(target=waiter, args=("Second",))
        t1.start()
        time.sleep(0.05)
        t2.start()
        time.sleep(0.05)
        rm.release("Holder", "R1")
        t1.join()
        t2.join()
        self.assertEqual(order, ["First", "Second"])

    def test_dfs_cycle_detection(self) -> None:
        acyclic = {"P1": {"P2"}, "P2": {"P3"}}
        cycle, _ = detect_cycle(acyclic)
        self.assertIsNone(cycle)

        cyclic = {"P1": {"P2"}, "P2": {"P3"}, "P3": {"P1"}}
        cycle, _ = detect_cycle(cyclic)
        self.assertIsNotNone(cycle)
        self.assertEqual(set(cycle), {"P1", "P2", "P3"})

    def test_deadlock_recovery_and_clean_release(self) -> None:
        rm = ResourceManager({"R1": 1, "R2": 1})
        specs = [
            WorkerSpec("P1", ["R1", "R2"], hold_delay=0.3, work_delay=0.1, timeout=5.0),
            WorkerSpec("P2", ["R2", "R1"], hold_delay=0.3, work_delay=0.1, timeout=5.0),
        ]
        runner = SimulationRunner(rm, use_detector=True, check_interval=0.1)
        self.assertEqual(runner.run(specs), 0)
        self.assertGreaterEqual(rm.deadlocks_detected, 1)
        self.assertIn(4, runner.results.values())
        self.assertIn(0, runner.results.values())
        self.assertEqual(rm.available, {"R1": 1, "R2": 1})

    def test_total_order_enforcement_and_prevention(self) -> None:
        rm = ResourceManager({"R1": 1, "R2": 1}, enforce_total_order=True)
        rm.request("P1", "R2", timeout=1.0)
        with self.assertRaises(OrderViolationError):
            rm.request("P1", "R1", timeout=1.0)
        rm.release("P1", "R2")

        specs = [
            WorkerSpec("P1", ["R1", "R2"], hold_delay=0.1, work_delay=0.1),
            WorkerSpec("P2", ["R2", "R1"], hold_delay=0.1, work_delay=0.1),
        ]
        runner = SimulationRunner(rm, use_detector=True, check_interval=0.1, use_total_order=True)
        runner.run(specs)
        self.assertEqual(rm.deadlocks_detected, 0)
        self.assertEqual(runner.results, {"P1": 0, "P2": 0})

    def test_missing_resource_error(self) -> None:
        rm = ResourceManager({"R1": 1})
        with self.assertRaises(ResourceNotFoundError):
            rm.request("P1", "R_DOES_NOT_EXIST", timeout=1.0)


if __name__ == "__main__":
    unittest.main()