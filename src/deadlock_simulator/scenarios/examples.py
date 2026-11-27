"""Jeux de scénarios déterministes pour la démonstration."""

import threading
import time

from ..core.resource_manager import ResourceManager
from ..domain.models import Process, Resource


def build_scenario(name: str):
    resources = [Resource("R1", "Ressource 1"), Resource("R2", "Ressource 2")]
    processes = [Process("P1", "Processus 1"), Process("P2", "Processus 2")]
    manager = ResourceManager(resources, processes)
    barrier = threading.Barrier(2)

    def activity(first: str, second: str):
        def run(shared: ResourceManager, stop: threading.Event) -> None:
            pid = "P1" if first == "R1" else "P2"
            if not shared.request(pid, first):
                return
            barrier.wait(timeout=1.0)
            if name == "deadlock":
                acquired = shared.request(pid, second)
                while not acquired and not stop.wait(0.02):
                    acquired = shared.request(pid, second)
            else:
                time.sleep(0.05)
                shared.release_all(pid)
        return run

    if name == "safe":
        # Les deux activités relâchent leur première ressource avant la seconde demande.
        activities = {
            "P1": activity("R1", "R2"),
            "P2": activity("R2", "R1"),
        }
    elif name == "deadlock":
        activities = {
            "P1": activity("R1", "R2"),
            "P2": activity("R2", "R1"),
        }
    else:
        raise ValueError(f"Scénario inconnu: {name}")
    return manager, activities
