import logging
from statistics import mean
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class PriceArbiter:
    """موتور انتخاب قیمت نهایی از چندین منبع با روش اکثریت/اجماع"""

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
        """
        ورودی: دیکشنری {نام_منبع: قیمت} (قیمت None یعنی در دسترس نبوده)
        خروجی: {price, method, details}
        """
        available = {name: price for name, price in sources.items() if price is not None}
        if not available:
            return {
                "price": default,
                "method": "fallback",
                "details": "هیچ منبعی در دسترس نیست، مقدار پیش‌فرض استفاده شد"
            }

        prices = list(available.values())
        names = list(available.keys())

        # حالت 1: اتفاق کامل (همه منابع در محدوده مجاز)
        if len(available) >= 2 and self._is_within_tolerance(prices):
            avg_price = mean(prices)
            return {
                "price": avg_price,
                "method": "consensus",
                "details": f"اجماع بین {names} با میانگین {avg_price:.2f}"
            }

        # حالت 2: یافتن نزدیک‌ترین دو منبع (اکثریت)
        best_pair = None
        best_diff = float('inf')
        src_keys = list(available.keys())
        for i in range(len(src_keys)):
            for j in range(i+1, len(src_keys)):
                diff = abs(available[src_keys[i]] - available[src_keys[j]])
                if diff < best_diff:
                    best_diff = diff
                    best_pair = (available[src_keys[i]], available[src_keys[j]], src_keys[i], src_keys[j])
        if best_pair:
            avg_pair = (best_pair[0] + best_pair[1]) / 2
            return {
                "price": avg_pair,
                "method": "two_sources",
                "details": f"توافق بین {best_pair[2]} و {best_pair[3]} با میانگین {avg_pair:.2f}"
            }

        # حالت 3: اختلاف کامل – برگرداندن اولین منبع
        first = next(iter(available.items()))
        return {
            "price": first[1],
            "method": "first_source",
            "details": f"اختلاف زیاد، استفاده از {first[0]} = {first[1]:.2f}"
        }
