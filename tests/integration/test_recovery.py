"""Validation intégrée du cycle, de la victime et du nettoyage des ressources."""

import unittest

from deadlock_simulator.core.detector import find_cycles
from deadlock_simulator.core.recovery import choose_victim, recover
from deadlock_simulator.core.resource_manager import ResourceManager
from deadlock_simulator.core.wait_for_graph import build_wait_for_graph
from deadlock_simulator.domain.models import EventType, Process, ProcessState, Resource


class RecoveryIntegrationTests(unittest.TestCase):
    def test_recovery_releases_victim_resources_logs_victim_and_removes_cycle(self) -> None:
        manager = ResourceManager(
            resources=[Resource("R1", "Ressource 1"), Resource("R2", "Ressource 2")],
            processes=[Process("P1", "Processus 1"), Process("P2", "Processus 2")],
        )
        manager.request("P1", "R1")
        manager.request("P2", "R2")
        manager.request("P1", "R2")
        manager.request("P2", "R1")

        cycles_before = find_cycles(build_wait_for_graph(manager))
        self.assertTrue(cycles_before)
        victim_id = choose_victim(cycles_before[0])
        victim_resources = set(manager.processes[victim_id].held_resources)

        with self.assertLogs("deadlock_simulator.core.recovery", level="WARNING") as logs:
            recover(manager, victim_id)

        victim = manager.processes[victim_id]
        self.assertEqual(victim.state, ProcessState.TERMINATED)
        self.assertEqual(victim.held_resources, set())
        self.assertFalse(find_cycles(build_wait_for_graph(manager)))
        self.assertTrue(
            any(
                event.event_type is EventType.VICTIM and event.process_id == victim_id
                for event in manager.events
            )
        )
        self.assertTrue(any(victim_id in message for message in logs.output))
        self.assertTrue(victim_resources)
        self.assertTrue(
            all(manager.owner_of(resource_id) is None for resource_id in victim_resources)
        )


if __name__ == "__main__":
    unittest.main()
