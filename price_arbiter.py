import logging
from statistics import mean
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PriceArbiter:
    def __init__(self, tolerance_percent: float = 2.0):
        self.tolerance_percent = tolerance_percent

    def _is_within_tolerance(self, prices: List[float]) -> bool:
        if not prices:
            return False
        min_p = min(prices)
        max_p = max(prices)
        diff = ((max_p - min_p) / min_p) * 100 if min_p > 0 else 100
        return diff <= self.tolerance_percent

    def resolve_price(self, sources: Dict[str, Optional[float]], default: float = None) -> Dict[str, Any]:
        available = {n: p for n, p in sources.items() if p is not None}
        if not available:
            return {"price": default, "method": "fallback", "details": "No source available"}

        prices = list(available.values())
        names = list(available.keys())

        if len(available) >= 2 and self._is_within_tolerance(prices):
            avg_price = mean(prices)
            return {"price": avg_price, "method": "consensus", "details": f"Sources: {names}"}

        best_pair = None
        best_diff = float('inf')
        src_keys = list(available.keys())
        for i in range(len(src_keys)):
            for j in range(i+1, len(src_keys)):
                p1 = available[src_keys[i]]
                p2 = available[src_keys[j]]
                diff = abs(p1 - p2)
                if diff < best_diff:
                    best_diff = diff
                    best_pair = (p1, p2, src_keys[i], src_keys[j])
        if best_pair:
            avg_pair = (best_pair[0] + best_pair[1]) / 2
            return {"price": avg_pair, "method": "two_sources", "details": f"Agreement between {best_pair[2]} and {best_pair[3]}"}

        first = next(iter(available.items()))
        return {"price": first[1], "method": "first_source", "details": f"Sources: {available}"}
