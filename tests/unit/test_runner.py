"""Tests des erreurs et de l'arrêt coopératif du runner concurrent."""

import threading
import unittest
from unittest.mock import patch

from deadlock_simulator.concurrency.runner import run_scenario_concurrently
from deadlock_simulator.core.resource_manager import ResourceManager
from deadlock_simulator.domain.models import Process, ProcessState, Resource


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ResourceManager(
            resources=[Resource("R1", "Ressource 1")],
            processes=[Process("P1", "Processus 1"), Process("P2", "Processus 2")],
        )

    def assert_resources_released(self) -> None:
        self.assertIsNone(self.manager.owner_of("R1"))
        self.assertEqual(self.manager.processes["P1"].held_resources, set())

    def test_normal_completion_terminates_process_and_releases_resource(self) -> None:
        def activity(manager: ResourceManager, stop: threading.Event) -> None:
            self.assertTrue(manager.request("P1", "R1"))

        run_scenario_concurrently(self.manager, {"P1": activity})

        self.assert_resources_released()
        self.assertEqual(self.manager.processes["P1"].state, ProcessState.TERMINATED)

    def test_activity_error_stops_workers_and_releases_resources(self) -> None:
        def failing(manager: ResourceManager, stop: threading.Event) -> None:
            manager.request("P1", "R1")
            raise ValueError("erreur de simulation")

        def cooperative(manager: ResourceManager, stop: threading.Event) -> None:
            stop.wait(2.0)

        with self.assertRaisesRegex(RuntimeError, "L'activité P1 a échoué") as caught:
            run_scenario_concurrently(self.manager, {"P1": failing, "P2": cooperative})

        self.assertIsInstance(caught.exception.__cause__, ValueError)
        self.assert_resources_released()
        self.assertEqual(self.manager.processes["P2"].state, ProcessState.TERMINATED)

    def test_timeout_requests_stop_and_releases_resources(self) -> None:
        def cooperative(manager: ResourceManager, stop: threading.Event) -> None:
            manager.request("P1", "R1")
            stop.wait(2.0)

        with self.assertRaisesRegex(TimeoutError, "arrêt coopératif effectué"):
            run_scenario_concurrently(self.manager, {"P1": cooperative}, timeout=0.03)

        self.assert_resources_released()
        self.assertEqual(self.manager.processes["P1"].state, ProcessState.TERMINATED)

    def test_keyboard_interrupt_requests_stop_and_releases_resources(self) -> None:
        def cooperative(manager: ResourceManager, stop: threading.Event) -> None:
            manager.request("P1", "R1")
            stop.wait(2.0)

        with patch("deadlock_simulator.concurrency.runner.time.sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                run_scenario_concurrently(self.manager, {"P1": cooperative})

        self.assert_resources_released()
        self.assertEqual(self.manager.processes["P1"].state, ProcessState.TERMINATED)

    def test_thread_start_failure_stops_started_worker_and_terminates_unstarted(self) -> None:
        real_start = threading.Thread.start
        start_count = 0

        def start_with_failure(thread: threading.Thread, *args: object, **kwargs: object) -> None:
            nonlocal start_count
            start_count += 1
            if start_count == 2:
                raise RuntimeError("échec de démarrage simulé")
            real_start(thread, *args, **kwargs)

        def cooperative(manager: ResourceManager, stop: threading.Event) -> None:
            manager.request("P1", "R1")
            stop.wait(2.0)

        with patch.object(threading.Thread, "start", start_with_failure):
            with self.assertRaisesRegex(RuntimeError, "Impossible de créer/démarrer"):
                run_scenario_concurrently(
                    self.manager,
                    {"P1": cooperative, "P2": lambda manager, stop: None},
                )

        self.assert_resources_released()
        self.assertEqual(self.manager.processes["P1"].state, ProcessState.TERMINATED)
        self.assertEqual(self.manager.processes["P2"].state, ProcessState.TERMINATED)


if __name__ == "__main__":
    unittest.main()
