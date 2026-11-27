from __future__ import annotations

import time


def detect_cycle(wfg: dict[str, set[str]]) -> tuple[list[str] | None, float]:
    """
    Run 3-color DFS on the Wait-For Graph.
    Returns (cycle_nodes_or_None, elapsed_ms).
    """
    t0 = time.perf_counter()
    # 0 = unvisited, 1 = visiting (on current stack), 2 = fully explored
    state: dict[str, int] = {}
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        state[node] = 1
        path.append(node)
        for neighbor in sorted(wfg.get(node, ())):
            n_state = state.get(neighbor, 0)
            if n_state == 1:
                idx = path.index(neighbor)
                return path[idx:]
            if n_state == 0:
                cycle = dfs(neighbor)
                if cycle is not None:
                    return cycle
        path.pop()
        state[node] = 2
        return None

    for start in sorted(wfg.keys()):
        if state.get(start, 0) == 0:
            found = dfs(start)
            if found is not None:
                return found, (time.perf_counter() - t0) * 1000.0

    return None, (time.perf_counter() - t0) * 1000.0