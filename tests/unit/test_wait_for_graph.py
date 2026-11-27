"""Validation du graphe d'attente processus -> processus."""

import unittest

from deadlock_simulator.core.resource_manager import ResourceManager
from deadlock_simulator.core.wait_for_graph import build_wait_for_graph
from deadlock_simulator.domain.models import Process, Resource


class WaitForGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ResourceManager(
            resources=[Resource("R1", "Ressource 1")],
            processes=[Process("P1", "Processus 1"), Process("P2", "Processus 2")],
        )

    def test_waiting_request_creates_edge_to_resource_owner(self) -> None:
        self.assertTrue(self.manager.request("P1", "R1"))
        self.assertFalse(self.manager.request("P2", "R1"))

        graph = build_wait_for_graph(self.manager)

        self.assertEqual(graph["P2"], {"P1"})
        self.assertEqual(graph["P1"], set())

    def test_releasing_resource_removes_wait_for_edge(self) -> None:
        self.manager.request("P1", "R1")
        self.manager.request("P2", "R1")
        self.assertEqual(build_wait_for_graph(self.manager)["P2"], {"P1"})

        self.manager.release_all("P1")

        graph = build_wait_for_graph(self.manager)
        self.assertEqual(graph["P2"], set())


if __name__ == "__main__":
    unittest.main()
