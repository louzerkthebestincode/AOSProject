from __future__ import annotations


def select_victim(cycle: list[str], allocations: dict[str, dict[str, int]]) -> str:
    """
    Victim selection policy: pick the process in the cycle holding the fewest
    total resource instances (tie-broken by the last process in the cycle).
    """
    if not cycle:
        raise ValueError("Cannot select a victim from an empty cycle.")
    return min(
        reversed(cycle),
        key=lambda pid: sum(allocations.get(pid, {}).values()),
    )


def verify_release(pid: str, allocations: dict[str, dict[str, int]]) -> bool:
    """Confirm that pid holds zero remaining resource instances."""
    return sum(allocations.get(pid, {}).values()) == 0