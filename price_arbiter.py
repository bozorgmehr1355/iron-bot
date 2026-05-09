import logging
from statistics import mean
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class PriceArbiter:
    def __init__(self, tolerance_percent: float = 2.0):
        self.tolerance_percent = tolerance_percent

    def _is_within_tolerance(self, prices: List[float]) -> bool:
        if not prices:
            return False
        min_p = min(prices)
        max_p = max(prices)
        if min_p == 0:
            return False
        diff_percent = ((max_p - min_p) / min_p) * 100
        return diff_percent <= self.tolerance_percent

    def resolve_price(self, sources: Dict[str, Optional[float]], default: float = None) -> Dict[str, Any]:
        available = {n: p for n, p in sources.items() if p is not None}
        if not available:
            return {"price": default, "method": "fallback", "details": "هیچ منبعی در دسترس نیست"}

        prices = list(available.values())
        names = list(available.keys())

        if len(available) >= 2 and self._is_within_tolerance(prices):
            avg = mean(prices)
            return {"price": avg, "method": "consensus", "details": f"اجماع بین {names}"}

        best_pair = None
        best_diff = float('inf')
        keys = list(available.keys())
        for i in range(len(keys)):
            for j in range(i+1, len(keys)):
                diff = abs(available[keys[i]] - available[keys[j]])
                if diff < best_diff:
                    best_diff = diff
                    best_pair = (available[keys[i]], available[keys[j]], keys[i], keys[j])
        if best_pair:
            avg_pair = (best_pair[0] + best_pair[1]) / 2
            return {"price": avg_pair, "method": "two_sources", "details": f"توافق بین {best_pair[2]} و {best_pair[3]}"}

        first = next(iter(available.items()))
        return {"price": first[1], "method": "first_source", "details": f"استفاده از {first[0]}"}
