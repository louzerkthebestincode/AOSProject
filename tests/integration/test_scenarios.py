"""Tests répétés des scénarios de démonstration concurrents."""

import unittest

from deadlock_simulator.concurrency.runner import run_scenario_concurrently
from deadlock_simulator.domain.models import EventType
from deadlock_simulator.scenarios.examples import build_scenario


class ScenarioIntegrationTests(unittest.TestCase):
    def test_safe_scenario_finishes_without_victim_and_releases_resources(self) -> None:
        for iteration in range(5):
            with self.subTest(iteration=iteration + 1):
                manager, activities = build_scenario("safe")
                run_scenario_concurrently(manager, activities, timeout=2.0)

                self.assertFalse(any(e.event_type is EventType.VICTIM for e in manager.events))
                self.assertTrue(all(manager.owner_of(rid) is None for rid in manager.resources))

    def test_deadlock_scenario_detects_victim_and_releases_resources(self) -> None:
        for iteration in range(5):
            with self.subTest(iteration=iteration + 1):
                manager, activities = build_scenario("deadlock")
                run_scenario_concurrently(manager, activities, timeout=2.0)

                victims = [e for e in manager.events if e.event_type is EventType.VICTIM]
                self.assertEqual(len(victims), 1)
                self.assertTrue(all(manager.owner_of(rid) is None for rid in manager.resources))


if __name__ == "__main__":
    unittest.main()
