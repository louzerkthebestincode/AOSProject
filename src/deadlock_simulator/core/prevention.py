from __future__ import annotations

from ..domain.models import OrderViolationError


class TotalOrderPolicy:
    """Prevents circular wait by assigning a strict total order to all resources."""

    def __init__(self, resource_ids: list[str] | set[str]) -> None:
        self.ranks: dict[str, int] = {
            res_id: idx for idx, res_id in enumerate(sorted(resource_ids))
        }

    def order_requests(self, resource_ids: list[str]) -> list[str]:
        """Sort a worker's resource list in strictly ascending global order."""
        return sorted(resource_ids, key=lambda r: self.ranks.get(r, float("inf")))

    def validate_request(self, pid: str, requested_res: str, held_resources: dict[str, int]) -> None:
        """Reject any request whose rank is <= the highest rank currently held by pid."""
        if not held_resources:
            return
        req_rank = self.ranks[requested_res]
        max_held_res = max(held_resources, key=lambda r: self.ranks[r])
        max_held_rank = self.ranks[max_held_res]
        if req_rank <= max_held_rank:
            raise OrderViolationError(
                f"Total order violation by {pid}: requested '{requested_res}' (rank {req_rank}) "
                f"while holding '{max_held_res}' (rank {max_held_rank})."
            )
