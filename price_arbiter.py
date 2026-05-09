import logging
from statistics import mean
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PriceArbiter:
    """موتور انتخاب و اعتبارسنجی قیمت از چندین منبع"""

    def __init__(self, tolerance_percent: float = 2.0):
        """
        tolerance_percent: حداکثر اختلاف مجاز بین منابع (درصد)
        """
        self.tolerance_percent = tolerance_percent

    def _is_within_tolerance(self, prices: List[float]) -> bool:
        """بررسی می‌کند که آیا تمام قیمت‌ها در محدوده قابل قبول هستند"""
        if not prices:
            return False
        min_p = min(prices)
        max_p = max(prices)
        diff_percent = ((max_p - min_p) / min_p) * 100 if min_p > 0 else 100
        return diff_percent <= self.tolerance_percent

    def resolve_price(self, sources: Dict[str, Optional[float]], default: float = None) -> Dict[str, Any]:
        """
        ورودی: دیکشنری {نام_منبع: قیمت} (قیمت None یعنی در دسترس نبوده)
        خروجی: دیکشنری شامل:
            - price: قیمت نهایی انتخاب شده
            - method: روش انتخاب (consensus, two_sources, fallback)
            - details: جزئیات منابع و اختلافات
        """
        available = {name: price for name, price in sources.items() if price is not None}
        if not available:
            logger.warning("هیچ منبع قیمتی در دسترس نیست. استفاده از Fallback.")
            return {
                "price": default,
                "method": "fallback",
                "details": "No source available"
            }

        prices = list(available.values())
        names = list(available.keys())

        # حالت 1: اتفاق کامل (همه منابع در محدوده مجاز)
        if len(available) >= 2 and self._is_within_tolerance(prices):
            avg_price = mean(prices)
            logger.info(f"Consensus price: {avg_price} from {names}")
            return {
                "price": avg_price,
                "method": "consensus",
                "details": f"Sources: {names}, values: {prices}"
            }

        # حالت 2: دو منبع همخوان (اکثریت)
        # ساده‌ترین روش: هر جفت را بررسی کن
        best_pair = None
        best_pair_diff = float('inf')
        source_names = list(available.keys())
        for i in range(len(source_names)):
            for j in range(i+1, len(source_names)):
                p1 = available[source_names[i]]
                p2 = available[source_names[j]]
                diff = abs(p1 - p2)
                if diff < best_pair_diff:
                    best_pair_diff = diff
                    best_pair = (p1, p2, source_names[i], source_names[j])
        if best_pair:
            avg_pair = (best_pair[0] + best_pair[1]) / 2
            logger.info(f"Two-source agreement: {avg_pair} from {best_pair[2]}, {best_pair[3]}")
            return {
                "price": avg_pair,
                "method": "two_sources",
                "details": f"Agreement between {best_pair[2]} and {best_pair[3]}"
            }

        # حالت 3: اختلاف کامل – نزدیک‌ترین به میانگین تاریخی را انتخاب کن (اگر نداری، اولین منبع)
        # فعلاً ساده: اولین منبع
        first_source = next(iter(available.items()))
        logger.warning(f"Full disagreement, using first source: {first_source[0]} = {first_source[1]}")
        return {
            "price": first_source[1],
            "method": "first_source",
            "details": f"Sources: {available}"
        }
