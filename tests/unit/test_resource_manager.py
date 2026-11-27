"""Tests unitaires des demandes, allocations et libérations de ressources."""

import unittest

from deadlock_simulator.core.resource_manager import ResourceManager
from deadlock_simulator.domain.models import Process, ProcessState, Resource


class ResourceManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ResourceManager(
            resources=[Resource("R1", "Ressource 1"), Resource("R2", "Ressource 2")],
            processes=[Process("P1", "Processus 1"), Process("P2", "Processus 2")],
        )

    def test_free_resource_is_allocated_to_requesting_process(self) -> None:
        acquired = self.manager.request("P1", "R1")

        self.assertTrue(acquired)
        self.assertEqual(self.manager.owner_of("R1"), "P1")
        self.assertIn("R1", self.manager.processes["P1"].held_resources)
        self.assertEqual(self.manager.processes["P1"].state, ProcessState.RUNNING)
        self.assertNotIn("R1", self.manager.processes["P2"].held_resources)

    def test_occupied_resource_puts_other_process_in_waiting_state(self) -> None:
        self.manager.request("P1", "R1")

        acquired = self.manager.request("P2", "R1")

        self.assertFalse(acquired)
        self.assertEqual(self.manager.owner_of("R1"), "P1")
        self.assertIn("R1", self.manager.processes["P1"].held_resources)
        self.assertNotIn("R1", self.manager.processes["P2"].held_resources)
        self.assertEqual(self.manager.processes["P2"].waiting_for, "R1")
        self.assertEqual(self.manager.processes["P2"].state, ProcessState.WAITING)

    def test_release_all_frees_every_owned_resource(self) -> None:
        self.manager.request("P1", "R1")
        self.manager.request("P1", "R2")

        self.manager.release_all("P1")

        self.assertIsNone(self.manager.owner_of("R1"))
        self.assertIsNone(self.manager.owner_of("R2"))
        self.assertEqual(self.manager.processes["P1"].held_resources, set())

    def test_unknown_process_id_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Processus inconnu: PX"):
            self.manager.request("PX", "R1")

    def test_unknown_resource_id_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Ressource inconnue: RX"):
            self.manager.request("P1", "RX")


if __name__ == "__main__":
    unittest.main()
