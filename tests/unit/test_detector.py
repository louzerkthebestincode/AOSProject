"""Tests unitaires de détection des cycles du graphe d'attente."""

import unittest

from deadlock_simulator.core.detector import find_cycles


class DetectorTests(unittest.TestCase):
    def test_acyclic_graph_has_no_cycles(self) -> None:
        graph = {"P1": {"P2"}, "P2": {"P3"}, "P3": set()}

        self.assertEqual(find_cycles(graph), [])

    def test_cycle_is_reported_with_starting_node_at_both_ends(self) -> None:
        graph = {"P1": {"P2"}, "P2": {"P1"}}

        cycles = find_cycles(graph)

        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0][0], cycles[0][-1])
        self.assertEqual(set(cycles[0][:-1]), {"P1", "P2"})


if __name__ == "__main__":
    unittest.main()
