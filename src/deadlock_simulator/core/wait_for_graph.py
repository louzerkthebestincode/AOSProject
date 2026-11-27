from __future__ import annotations

from collections import deque


def build_wait_for_graph(
    allocations: dict[str, dict[str, int]],
    wait_queues: dict[str, deque[str]],
) -> dict[str, set[str]]:
    """
    Build a directed Wait-For Graph (WFG): {waiter_pid: {holder_pid, ...}}.
    Works for both single-instance and multi-instance resources.
    """
    holders_by_resource: dict[str, set[str]] = {}
    for pid, held in allocations.items():
        for res_id, count in held.items():
            if count > 0:
                holders_by_resource.setdefault(res_id, set()).add(pid)

    wfg: dict[str, set[str]] = {}
    for res_id, queue in wait_queues.items():
        holders = holders_by_resource.get(res_id, set())
        for waiter in queue:
            deps = {h for h in holders if h != waiter}
            if deps:
                wfg.setdefault(waiter, set()).update(deps)
    return wfg